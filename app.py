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

init_db()

# --- CARICAMENTO DATI ---
def get_all_data():
    with sqlite3.connect(DB_NAME) as conn:
        df_t = pd.read_sql_query("SELECT * FROM tasks ORDER BY Data_Prevista ASC", conn)
        df_team = pd.read_sql_query("SELECT nome FROM team", conn)
        df_canali = pd.read_sql_query("SELECT nome FROM canali", conn)
    list_t = df_team["nome"].tolist() if not df_team.empty else ["Marco", "Giulia"]
    list_c = df_canali["nome"].tolist() if not df_canali.empty else ["Instagram", "Facebook"]
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
                (st.session_state.input_titolo, curr_date.strftime("%Y-%m-%d"), ", ".join(st.session_state.input_canali), 
                 st.session_state.input_testo, st.session_state.input_link, 
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
    st.text_input("Link Risorsa (URL)", key="input_link")
    st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'], key="input_foto")
    st.multiselect("Canali:", canali_list, key="input_canali")
    st.date_input("Inizio", datetime.now(), key="input_data_inizio")
    st.date_input("Fine", datetime.now() + timedelta(days=7), key="input_data_fine")
    st.number_input("Frequenza (gg)", min_value=1, value=1, key="input_frequenza")
    st.multiselect("Assegna a:", team_list, key="input_assegnati")
    if st.button("Genera Piano", type="primary", use_container_width=True):
        genera_piano()

tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        df_vis = df_task.copy()
        df_vis['Data_Prevista'] = pd.to_datetime(df_vis['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_vis['Anteprima'] = df_vis['Foto_Bytes'].apply(get_image_base64)
        df_vis.insert(0, "Sel.", False)
        
        col_view = ["Sel.", "Anteprima", "Titolo", "Link", "Data_Prevista", "Stato"]
        
        edited = st.data_editor(
            df_vis[col_view],
            column_config={
                "Sel.": st.column_config.CheckboxColumn("", width="small"),
                "Anteprima": st.column_config.ImageColumn("Foto"),
                "Link": st.column_config.LinkColumn("Link", display_text="Apri"),
            },
            disabled=[c for c in col_view if c != "Sel."],
            hide_index=True, use_container_width=True, key="editor", row_height=70
        )
        
        selected_indices = edited[edited["Sel."] == True].index.tolist()
        
        if selected_indices:
            st.divider()
            for idx in selected_indices:
                task = df_task.iloc[idx]
                tid = task["ID"]
                with st.expander(f"📦 MODIFICA TASK: {task['Titolo']}", expanded=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        # AGGIUNTA LINK NELL'EXPANDER
                        old_link = task["Link"] if task["Link"] else ""
                        new_link = st.text_input("🔗 Link (URL):", old_link, key=f"exp_link_{tid}")
                        
                        new_txt = st.text_area("📝 Testo:", task["Contenuto"], key=f"exp_txt_{tid}", height=120)
                        
                        if st.button("💾 Salva Modifiche", key=f"save_{tid}", type="primary"):
                            run_query("UPDATE tasks SET Contenuto = ?, Link = ? WHERE ID = ?", (new_txt, new_link, tid))
                            st.rerun()
                    with c2:
                        if task["Foto_Bytes"]: st.image(task["Foto_Bytes"])
                    
                    st.divider()
                    ca1, ca2, ca3 = st.columns([2, 2, 1])
                    if task["Stato"] != "🟢 Completato":
                        user = ca1.selectbox("Chi?", team_list, key=f"u_{tid}")
                        if ca2.button("✅ Fatto", key=f"f_{tid}", use_container_width=True):
                            run_query("UPDATE tasks SET Stato='🟢 Completato', Completato_da=?, Data_Fine=? WHERE ID=?", (user, datetime.now().strftime("%d/%m %H:%M"), tid))
                            st.rerun()
                    if ca3.button("🗑️", key=f"d_{tid}", use_container_width=True):
                        run_query("DELETE FROM tasks WHERE ID = ?", (tid,))
                        st.rerun()
    else:
        st.info("Nessun task presente.")

with tab2:
    st.subheader("Configurazione")
    st.write("Usa la sidebar per creare task. Qui puoi gestire Team e Canali se implementati.")
