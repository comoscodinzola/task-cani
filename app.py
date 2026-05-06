import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import base64
import math

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
    run_query('CREATE TABLE IF NOT EXISTS team (nome TEXT UNIQUE)')
    run_query('CREATE TABLE IF NOT EXISTS canali (nome TEXT UNIQUE)')

init_db()

# --- CARICAMENTO DATI ---
def get_all_data():
    with sqlite3.connect(DB_NAME) as conn:
        df_t = pd.read_sql_query("SELECT * FROM tasks ORDER BY Data_Prevista ASC", conn)
        df_team = pd.read_sql_query("SELECT nome FROM team", conn)
        df_canali = pd.read_sql_query("SELECT nome FROM canali", conn)
    return df_t, df_team["nome"].tolist(), df_canali["nome"].tolist()

def get_image_base64(image_bytes):
    if not image_bytes: return None
    try:
        return f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
    except: return None

df_task, team_list, canali_list = get_all_data()

# --- INTERFACCIA ---
st.title("📅 Social Task Manager Pro")

# Sidebar per inserimento
with st.sidebar:
    st.header("🚀 Nuovo Piano")
    st.text_input("Titolo *", key="input_titolo")
    st.text_area("Testo Post *", key="input_testo")
    st.date_input("Inizio", datetime.now(), key="input_data_inizio")
    st.date_input("Fine", datetime.now() + timedelta(days=7), key="input_data_fine")
    if st.button("Genera Piano", type="primary", use_container_width=True):
        # ... logica inserimento (omessa per brevità, rimane uguale)
        st.rerun()

tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        # --- LOGICA PAGINAZIONE ---
        records_per_page = 10
        total_pages = math.ceil(len(df_task) / records_per_page)
        
        # Inizializza lo stato della pagina
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1

        # Filtro del dataframe per la pagina corrente
        start_idx = (st.session_state.current_page - 1) * records_per_page
        end_idx = start_idx + records_per_page
        df_page = df_task.iloc[start_idx:end_idx].copy()

        # Preparazione visualizzazione
        df_page['Data'] = pd.to_datetime(df_page['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_page['Foto'] = df_page['Foto_Bytes'].apply(get_image_base64)
        df_page.insert(0, "📂", False)
        
        # Tabella con righe basse
        edited = st.data_editor(
            df_page[["📂", "Foto", "Titolo", "Data", "Stato"]],
            column_config={
                "📂": st.column_config.CheckboxColumn("Mod.", width="small"),
                "Foto": st.column_config.ImageColumn("Anteprima"),
                "Data": "Scadenza"
            },
            disabled=["Foto", "Titolo", "Data", "Stato"],
            hide_index=True, 
            use_container_width=True, 
            key=f"editor_page_{st.session_state.current_page}", 
            row_height=35
        )

        # --- CONTROLLI PAGINAZIONE (Stile immagine richiesta) ---
        col_pag1, col_pag2, col_pag3, col_pag4, col_pag5 = st.columns([1, 1, 2, 1, 1])
        
        with col_pag2:
            if st.button("❮", disabled=(st.session_state.current_page == 1)):
                st.session_state.current_page -= 1
                st.rerun()
        
        with col_pag3:
            st.markdown(f"<p style='text-align: center; background-color: #e1f5fe; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; margin: auto; font-weight: bold; color: #0288d1;'>{st.session_state.current_page}</p>", unsafe_allow_html=True)
        
        with col_pag4:
            if st.button("❯", disabled=(st.session_state.current_page == total_pages)):
                st.session_state.current_page += 1
                st.rerun()
        
        st.caption(f"Pagina {st.session_state.current_page} di {total_pages} ({len(df_task)} task totali)")

        # LOGICA MODIFICA/ELIMINAZIONE (basata sull'ID reale del task)
        selected_rows = edited[edited["📂"] == True].index.tolist()
        if selected_rows:
            for idx_in_page in selected_rows:
                # Recuperiamo l'ID corretto dal DataFrame della pagina
                task = df_page.iloc[idx_in_page]
                tid = task["ID"]
                with st.expander(f"⚙️ GESTIONE: {task['Titolo']}", expanded=True):
                    # ... (Pulsanti Salva/Elimina rimangono uguali alle versioni precedenti)
                    if st.button("🗑️ Elimina Definitivamente", key=f"del_{tid}"):
                        run_query("DELETE FROM tasks WHERE ID = ?", (tid,))
                        st.rerun()
    else:
        st.info("Nessun task in archivio.")
