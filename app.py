import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import base64

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Social Task Manager Pro", layout="wide", page_icon="📅")

DB_NAME = "social_tasks.db"

# --- FUNZIONI DI SUPPORTO ---
def get_image_base64(image_bytes):
    if not image_bytes: return None
    try:
        base64_str = base64.b64encode(image_bytes).decode()
        return f"data:image/png;base64,{base64_str}"
    except: return None

# --- GESTIONE DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                  Titolo TEXT, Data_Prevista TEXT, Canali TEXT, Contenuto TEXT, 
                  Link TEXT, Foto_Nome TEXT, Foto_Bytes BLOB, Assegnato_a TEXT, 
                  Stato TEXT, Completato_da TEXT, Data_Fine TEXT)''')
    
    c.execute("PRAGMA table_info(tasks)")
    existing_cols = [col[1] for col in c.fetchall()]
    migrazioni = [("Titolo", "TEXT DEFAULT 'Senza Titolo'"), ("Link", "TEXT"), ("Assegnato_a", "TEXT")]
    for col_name, col_type in migrazioni:
        if col_name not in existing_cols:
            try:
                c.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
            except: pass
            
    c.execute('CREATE TABLE IF NOT EXISTS team (nome TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS canali (nome TEXT UNIQUE)')
    conn.commit()
    conn.close()

def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()

def pulisci_scaduti_vecchi():
    limite_cancellazione = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    run_query("DELETE FROM tasks WHERE Stato = '🔴 Da fare' AND Data_Prevista < ?", (limite_cancellazione,))

init_db()
pulisci_scaduti_vecchi()

# --- CARICAMENTO DATI ---
def get_all_data():
    with sqlite3.connect(DB_NAME) as conn:
        df_t = pd.read_sql_query("SELECT * FROM tasks ORDER BY Data_Prevista ASC", conn)
        df_team = pd.read_sql_query("SELECT nome FROM team", conn)
        df_canali = pd.read_sql_query("SELECT nome FROM canali", conn)
    list_t = df_team["nome"].tolist() if not df_team.empty else ["Marco", "Giulia"]
    list_c = df_canali["nome"].tolist() if not df_canali.empty else ["Instagram", "Facebook", "TikTok"]
    return df_t, list_t, list_c

df_task, team_list, canali_list = get_all_data()

# --- LOGICA GENERAZIONE PIANO ---
def genera_piano():
    if not st.session_state.input_titolo or not st.session_state.input_testo:
        st.error("Inserisci Titolo e Testo!")
        return
    with sqlite3.connect(DB_NAME) as conn:
        curr_date = st.session_state.input_data_inizio
        while curr_date <= st.session_state.input_data_fine:
            conn.execute('''INSERT INTO tasks 
                (Titolo, Data_Prevista, Canali, Contenuto, Link, Foto_Nome, Foto_Bytes, Assegnato_a, Stato, Completato_da, Data_Fine) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (st.session_state.input_titolo, curr_date.strftime("%Y-%m-%d"), 
                 ", ".join(st.session_state.input_canali), st.session_state.input_testo, 
                 st.session_state.input_link, 
                 st.session_state.input_foto.name if st.session_state.input_foto else "",
                 st.session_state.input_foto.getvalue() if st.session_state.input_foto else None,
                 ", ".join(st.session_state.input_assegnati), "🔴 Da fare", "-", "-"))
            curr_date += timedelta(days=st.session_state.input_frequenza)
    st.rerun()

# --- INTERFACCIA UTENTE ---
st.title("📅 Social Task Manager Pro")

with st.sidebar:
    st.header("🚀 Nuovo Piano")
    st.text_input("Titolo *", key="input_titolo")
    st.text_area("Testo Post *", key="input_testo")
    st.text_input("Link Risorsa (URL)", key="input_link", placeholder="https://...")
    st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'], key="input_foto")
    st.multiselect("Canali:", canali_list, key="input_canali")
    st.date_input("Inizio", datetime.now(), key="input_data_inizio")
    st.date_input("Fine", datetime.now() + timedelta(days=7), key="input_data_fine")
    st.number_input("Ogni quanti giorni?", min_value=1, value=1, key="input_frequenza")
    st.multiselect("Assegna a:", team_list, key="input_assegnati")
    if st.button("Genera Piano", type="primary", use_container_width=True):
        genera_piano()

tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        df_vis = df_task.copy()
        df_vis['Data_Prevista'] = pd.to_datetime(df_vis['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_vis['Anteprima'] = df_vis['Foto_Bytes'].apply(get_image_base64)
        df_vis.insert(0, "Edit", False) # Colonna per aprire i dettagli
        df_vis["🗑️"] = False # Nuova colonna per eliminazione rapida
        
        # Colonne da visualizzare nella tabella
        cols_to_show = ["Edit", "Anteprima", "Titolo", "Link", "Data_Prevista", "Stato", "🗑️"]
        
        edited = st.data_editor(
            df_vis[cols_to_show],
            column_config={
                "Edit": st.column_config.CheckboxColumn("Dettagli", width="small"),
                "Anteprima": st.column_config.ImageColumn("Foto"),
                "Link": st.column_config.LinkColumn("Link", display_text="Apri"),
                "🗑️": st.column_config.CheckboxColumn("Elimina", width="small"),
            },
            disabled=["Anteprima", "Titolo", "Link", "Data_Prevista", "Stato"],
            hide_index=True, use_container_width=True, key="main_editor", row_height=75
        )
        
        # LOGICA ELIMINAZIONE RAPIDA (CESTINO)
        deleted_indices = edited[edited["🗑️"] == True].index.tolist()
        if deleted_indices:
            for idx in deleted_indices:
                tid = df_task.iloc[idx]["ID"]
                run_query("DELETE FROM tasks WHERE ID = ?", (tid,))
            st.rerun()

        # LOGICA APERTURA DETTAGLI (EDIT)
        selected_indices = edited[edited["Edit"] == True].index.tolist()
        
        if selected_indices:
            st.divider()
            for idx in selected_indices:
                task = df_task.iloc[idx]
                tid = task["ID"]
                with st.expander(f"📦 MODIFICA: {task['Titolo']} ({task['Data_Prevista']})", expanded=True):
                    c1, c2 = st.columns([3, 1.5])
                    with c1:
                        current_link = str(task["Link"]).strip() if task["Link"] else ""
                        st.text_input("🔗 Link (URL):", value=current_link, key=f"exp_link_{tid}")
                        
                        if current_link and current_link != "None" and current_link != "":
                            st.link_button("🚀 Vai al Link", current_link)
                        
                        st.text_area("📝 Testo:", value=task["Contenuto"], key=f"exp_txt_{tid}", height=150)
                        
                        if st.button("💾 Salva Modifiche", key=f"save_btn_{tid}", type="primary"):
                            nuovo_link = st.session_state[f"exp_link_{tid}"]
                            nuovo_testo = st.session_state[f"exp_txt_{tid}"]
                            run_query("UPDATE tasks SET Contenuto = ?, Link = ? WHERE ID = ?", (nuovo_testo, nuovo_link, tid))
                            st.rerun()
                            
                    with c2:
                        if task["Foto_Bytes"]:
                            st.image(task["Foto_Bytes"])
                            st.download_button(
                                label="📥 Scarica Foto",
                                data=task["Foto_Bytes"],
                                file_name=f"task_{tid}.png",
                                mime="image/png",
                                key=f"dl_{tid}",
                                use_container_width=True
                            )
                        else:
                            st.info("Nessuna immagine")
                    
                    st.divider()
                    ca1, ca2 = st.columns([2, 1])
                    if task["Stato"] != "🟢 Completato":
                        user = ca1.selectbox("Chi completa?", team_list, key=f"u_{tid}")
                        if ca2.button("✅ Segna come Fatto", key=f"f_{tid}", use_container_width=True):
                            run_query("UPDATE tasks SET Stato='🟢 Completato', Completato_da=?, Data_Fine=? WHERE ID=?", 
                                     (user, datetime.now().strftime("%d/%m %H:%M"), tid))
                            st.rerun()
                    else:
                        st.success(f"Completato da {task['Completato_da']} il {task['Data_Fine']}")
    else:
        st.info("Nessun task in programma.")

with tab2:
    st.subheader("Configurazione")
    col1, col2 = st.columns(2)
    with col1:
        membro = st.text_input("Nuovo membro Team:")
        if st.button("Aggiungi"):
            if membro:
                run_query("INSERT OR IGNORE INTO team (nome) VALUES (?)", (membro,))
                st.rerun()
        st.write("Team:", team_list)
    with col2:
        canale = st.text_input("Nuovo Canale:")
        if st.button("Aggiungi Canale"):
            if canale:
                run_query("INSERT OR IGNORE INTO canali (nome) VALUES (?)", (canale,))
                st.rerun()
        st.write("Canali:", canali_list)
