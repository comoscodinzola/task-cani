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

with st.sidebar:
    st.header("🚀 Nuovo Piano")
    st.text_input("Titolo *", key="input_titolo")
    st.text_area("Testo Post *", key="input_testo")
    st.date_input("Inizio", datetime.now(), key="input_data_inizio")
    st.date_input("Fine", datetime.now() + timedelta(days=7), key="input_data_fine")
    if st.button("Genera Piano", type="primary", use_container_width=True):
        # Logica di generazione (semplificata per focus su paginazione)
        st.rerun()

tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        # --- LOGICA PAGINAZIONE ---
        if 'page' not in st.session_state: st.session_state.page = 1
        per_page = 10
        total_p = math.ceil(len(df_task) / per_page)
        
        start = (st.session_state.page - 1) * per_page
        end = start + per_page
        df_page = df_task.iloc[start:end].copy()

        # Preparazione DataFrame
        df_page['Data'] = pd.to_datetime(df_page['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_page['Foto'] = df_page['Foto_Bytes'].apply(get_image_base64)
        df_page.insert(0, "📂", False)
        
        # Tabella Compatta (Key fissa per non perdere la selezione)
        edited = st.data_editor(
            df_page[["📂", "Foto", "Titolo", "Data", "Stato"]],
            column_config={
                "📂": st.column_config.CheckboxColumn("Vedi", width="small"),
                "Foto": st.column_config.ImageColumn("Anteprima"),
            },
            disabled=["Foto", "Titolo", "Data", "Stato"],
            hide_index=True, use_container_width=True, key="main_task_editor", row_height=35
        )

        # --- CONTROLLI PAGINAZIONE (Stile richiesto) ---
        c_pag1, c_pag2, c_pag3, c_pag4, c_pag5 = st.columns([2, 1, 1, 1, 2])
        with c_pag2:
            if st.button("❮", disabled=(st.session_state.page == 1)):
                st.session_state.page -= 1
                st.rerun()
        with c_pag3:
            # Cerchietto con numero pagina
            st.markdown(f"""<div style='text-align: center; background-color: #f0fdf4; border: 1px solid #dcfce7; 
                        border-radius: 50%; width: 35px; height: 35px; line-height: 35px; margin: auto; 
                        font-weight: bold; color: #16a34a;'>{st.session_state.page}</div>""", unsafe_allow_html=True)
        with c_pag4:
            if st.button("❯", disabled=(st.session_state.page == total_p)):
                st.session_state.page += 1
                st.rerun()

        # --- VISUALIZZAZIONE DETTAGLI ---
        # Verifichiamo quali righe della pagina corrente sono state selezionate
        selection = edited[edited["📂"] == True]
        
        if not selection.empty:
            st.divider()
            for idx in selection.index:
                # Usiamo l'indice della pagina per recuperare il task dal DataFrame filtrato
                task = df_page.loc[idx]
                tid = task["ID"]
                
                with st.expander(f"📦 DETTAGLI: {task['Titolo']} ({task['Data']})", expanded=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        new_txt = st.text_area("Testo Post:", value=task["Contenuto"], key=f"txt_{tid}")
                        b1, b2 = st.columns(2)
                        if b1.button("💾 Salva", key=f"s_{tid}", type="primary"):
                            run_query("UPDATE tasks SET Contenuto = ? WHERE ID = ?", (new_txt, tid))
                            st.rerun()
                        if b2.button("🗑️ Elimina", key=f"d_{tid}"):
                            run_query("DELETE FROM tasks WHERE ID = ?", (tid,))
                            st.rerun()
                    with col2:
                        if task["Foto_Bytes"]: st.image(task["Foto_Bytes"])
    else:
        st.info("Nessun task.")

with tab2:
    st.subheader("Configurazione")
    # ... (Il resto rimane uguale)
