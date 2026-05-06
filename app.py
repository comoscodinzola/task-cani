import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import base64

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Social Task Manager Pro", layout="wide", page_icon="📅")

DB_NAME = "social_tasks.db"

# --- FUNZIONI DATABASE ---
def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def init_db():
    run_query('''CREATE TABLE IF NOT EXISTS tasks
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                  Titolo TEXT, Data_Prevista TEXT, Canali TEXT, Contenuto TEXT, 
                  Link TEXT, Foto_Nome TEXT, Foto_Bytes BLOB, Assegnato_a TEXT, 
                  Stato TEXT, Completato_da TEXT, Data_Fine TEXT)''')
    
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(tasks)")
        existing_cols = [col[1] for col in c.fetchall()]
        if "Titolo" not in existing_cols: run_query("ALTER TABLE tasks ADD COLUMN Titolo TEXT DEFAULT 'Senza Titolo'")
        if "Link" not in existing_cols: run_query("ALTER TABLE tasks ADD COLUMN Link TEXT")
        if "Assegnato_a" not in existing_cols: run_query("ALTER TABLE tasks ADD COLUMN Assegnato_a TEXT")
    
    run_query('CREATE TABLE IF NOT EXISTS team (nome TEXT UNIQUE)')
    run_query('CREATE TABLE IF NOT EXISTS canali (nome TEXT UNIQUE)')

init_db()

# --- CARICAMENTO DATI ---
def get_all_data():
    with sqlite3.connect(DB_NAME) as conn:
        df_t = pd.read_sql_query("SELECT * FROM tasks ORDER BY Data_Prevista ASC", conn)
        df_team = pd.read_sql_query("SELECT nome FROM team", conn)
        df_canali = pd.read_sql_query("SELECT nome FROM canali", conn)
    list_t = df_team["nome"].tolist() if not df_team.empty else ["Marco", "Giulia"]
    list_c = df_canali["nome"].tolist() if not df_canali.empty else ["Instagram", "Facebook", "TikTok"]
    return df_t, list_t, list_c

def get_image_base64(image_bytes):
    if not image_bytes: return None
    try:
        return f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
    except: return None

df_task, team_list, canali_list = get_all_data()

# --- INTERFACCIA ---
st.title("📅 Social Task Manager Pro")

with st.sidebar:
    st.header("🚀 Nuovo Piano")
    st.text_input("Titolo *", key="input_titolo")
    st.text_area("Testo Post *", key="input_testo")
    st.text_input("Link Risorsa (URL)", key="input_link")
    st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'], key="input_foto")
    st.multiselect("Canali:", canali_list, key="input_canali")
    st.date_input("Inizio", datetime.now(), key="input_data_inizio")
    st.date_input("Fine", datetime.now() + timedelta(days=7), key="input_data_fine")
    st.number_input("Ogni quanti giorni?", min_value=1, value=1, key="input_frequenza")
    st.multiselect("Assegna a:", team_list, key="input_assegnati")
    
    if st.button("Genera Piano", type="primary", use_container_width=True):
        if st.session_state.input_titolo and st.session_state.input_testo:
            curr = st.session_state.input_data_inizio
            while curr <= st.session_state.input_data_fine:
                run_query('''INSERT INTO tasks (Titolo, Data_Prevista, Canali, Contenuto, Link, Foto_Nome, Foto_Bytes, Assegnato_a, Stato, Completato_da, Data_Fine) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (st.session_state.input_titolo, curr.strftime("%Y-%m-%d"), ", ".join(st.session_state.input_canali), 
                           st.session_state.input_testo, st.session_state.input_link, 
                           st.session_state.input_foto.name if st.session_state.input_foto else "",
                           st.session_state.input_foto.getvalue() if st.session_state.input_foto else None,
                           ", ".join(st.session_state.input_assegnati), "🔴 Da fare", "-", "-"))
                curr += timedelta(days=st.session_state.input_frequenza)
            st.rerun()

tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        df_vis = df_task.copy()
        df_vis['Data'] = pd.to_datetime(df_vis['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_vis['Foto'] = df_vis['Foto_Bytes'].apply(get_image_base64)
        df_vis.insert(0, "📂", False)
        
        # --- MODIFICA RICHIESTA: Altezza righe dimezzata e visualizzazione limitata ---
        # row_height=35 riduce l'altezza. 
        # L'altezza totale (height) calcolata per 10 record è circa 400px (35*10 + header)
        edited = st.data_editor(
            df_vis[["📂", "Foto", "Titolo", "Link", "Data", "Stato"]],
            column_config={
                "📂": st.column_config.CheckboxColumn("Apri", width="small"),
                "Foto": st.column_config.ImageColumn("Anteprima"),
                "Link": st.column_config.LinkColumn("Link", display_text="Apri"),
                "Data": "Scadenza"
            },
            disabled=["Foto", "Titolo", "Link", "Data", "Stato"],
            hide_index=True, 
            use_container_width=True, 
            key="main_editor", 
            row_height=35, # Altezza dimezzata
            height=400    # Mostra circa 10 record per volta
        )
        
        selected_rows = edited[edited["📂"] == True].index.tolist()
        
        if selected_rows:
            st.divider()
            for idx in selected_rows:
                task = df_task.iloc[idx]
                tid = task["ID"]
                d_format = datetime.strptime(task['Data_Prevista'], '%Y-%m-%d').strftime('%d-%m-%Y')
                
                with st.expander(f"⚙️ GESTIONE: {task['Titolo']} ({d_format})", expanded=True):
                    col_left, col_right = st.columns([3, 1.5])
                    with col_left:
                        l_val = task["Link"] if task["Link"] and str(task["Link"]) != "None" else ""
                        new_l = st.text_input("Link Risorsa:", value=l_val, key=f"l_{tid}")
                        if new_l: st.link_button("🚀 Apri Link", new_l)
                        new_t = st.text_area("Testo Post:", value=task["Contenuto"], key=f"t_{tid}", height=150)
                        
                        b_col1, b_col2 = st.columns(2)
                        if b_col1.button("💾 Salva", key=f"save_{tid}", type="primary", use_container_width=True):
                            run_query("UPDATE tasks SET Contenuto = ?, Link = ? WHERE ID = ?", (new_t, new_l, tid))
                            st.rerun()
                        if b_col2.button("🗑️ ELIMINA", key=f"del_{tid}", use_container_width=True):
                            run_query("DELETE FROM tasks WHERE ID = ?", (tid,))
                            st.rerun()

                    with col_right:
                        if task["Foto_Bytes"]:
                            st.image(task["Foto_Bytes"])
                        else:
                            st.info("No foto")
                    
                    if task["Stato"] != "🟢 Completato":
                        c1, c2 = st.columns([2, 1])
                        user = c1.selectbox("Chi?", team_list, key=f"u_{tid}")
                        if c2.button("✅ Fatto", key=f"f_{tid}", use_container_width=True):
                            run_query("UPDATE tasks SET Stato='🟢 Completato', Completato_da=?, Data_Fine=? WHERE ID=?", 
                                     (user, datetime.now().strftime("%d/%m %H:%M"), tid))
                            st.rerun()
    else:
        st.info("Nessun task.")

with tab2:
    st.subheader("Configurazione")
    cl1, cl2 = st.columns(2)
    with cl1:
        m_in = st.text_input("Nuovo Membro:")
        if st.button("Aggiungi Membro"):
            if m_in: run_query("INSERT OR IGNORE INTO team (nome) VALUES (?)", (m_in,))
            st.rerun()
    with cl2:
        c_in = st.text_input("Nuovo Canale:")
        if st.button("Aggiungi Canale"):
            if c_in: run_query("INSERT OR IGNORE INTO canali (nome) VALUES (?)", (c_in,))
            st.rerun()
