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
    """Crea le tabelle se non esistono e aggiunge le colonne mancanti"""
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Crea tabella tasks
        c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                     (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                      Titolo TEXT, Data_Prevista TEXT, Canali TEXT, 
                      Contenuto TEXT, Link TEXT, Foto_Nome TEXT, 
                      Foto_Bytes BLOB, Assegnato_a TEXT, Stato TEXT, 
                      Completato_da TEXT, Data_Fine TEXT)''')
        
        # Crea tabelle di configurazione
        c.execute('CREATE TABLE IF NOT EXISTS team (nome TEXT PRIMARY KEY)')
        c.execute('CREATE TABLE IF NOT EXISTS canali (nome TEXT PRIMARY KEY)')
        conn.commit()

def get_all_data_fresh():
    """Legge i dati dal DB assicurandosi che le tabelle esistano"""
    init_db() # Forza la creazione delle tabelle prima di ogni lettura
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df_t = pd.read_sql_query("SELECT * FROM tasks ORDER BY ID DESC", conn)
            df_team = pd.read_sql_query("SELECT nome FROM team", conn)
            df_canali = pd.read_sql_query("SELECT nome FROM canali", conn)
        
        t_list = df_team["nome"].tolist() if not df_team.empty else ["Membro 1"]
        c_list = df_canali["nome"].tolist() if not df_canali.empty else ["Instagram"]
        return df_t, t_list, c_list
    except Exception as e:
        # Se c'è ancora un errore (es. tabella bloccata), restituisce dataframe vuoti
        return pd.DataFrame(), ["Membro 1"], ["Instagram"]

def get_image_base64(image_bytes):
    if not image_bytes: return None
    try: return f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
    except: return None

# --- CARICAMENTO DATI ---
df_task, team_list, canali_list = get_all_data_fresh()

# --- SIDEBAR: INSERIMENTO ---
with st.sidebar:
    st.header("🚀 Nuovo Piano")
    titolo_in = st.text_input("Titolo *")
    testo_in = st.text_area("Testo Post *")
    link_in = st.text_input("Link (es. https://...)")
    foto_in = st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'])
    
    if st.button("Genera Piano", type="primary", use_container_width=True):
        if titolo_in and testo_in:
            data_ora = datetime.now().strftime("%Y-%m-%d")
            run_query('''INSERT INTO tasks (Titolo, Data_Prevista, Contenuto, Link, Foto_Bytes, Stato) 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (titolo_in, data_ora, testo_in, link_in, 
                       foto_in.getvalue() if foto_in else None, "🔴 Da fare"))
            st.rerun()

# --- MAIN ---
st.title("📅 Social Task Manager Pro")
tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        # Paginazione
        if 'page' not in st.session_state: st.session_state.page = 1
        per_page = 10
        total_p = math.ceil(len(df_task) / per_page)
        start = (st.session_state.page - 1) * per_page
        df_page = df_task.iloc[start:start+per_page].copy()

        # Prepariamo la visualizzazione
        df_page['Foto'] = df_page['Foto_Bytes'].apply(get_image_base64)
        df_page.insert(0, "📂", False)
        
        edited = st.data_editor(
            df_page[["📂", "Foto", "Titolo", "Stato"]],
            column_config={
                "📂": st.column_config.CheckboxColumn("Vedi", width="small"),
                "Foto": st.column_config.ImageColumn("Anteprima"),
            },
            disabled=["Foto", "Titolo", "Stato"],
            hide_index=True, use_container_width=True, key="editor_vFinal", row_height=35
        )

        selected_rows = edited[edited["📂"] == True]
        if not selected_rows.empty:
            idx = selected_rows.index[0]
            task_id = df_page.loc[idx, "ID"]
            
            # Rileggiamo il record specifico
            with sqlite3.connect(DB_NAME) as conn:
                t_db = pd.read_sql_query("SELECT * FROM tasks WHERE ID=?", conn, params=(int(task_id),)).iloc[0]

            with st.expander(f"⚙️ GESTIONE: {t_db['Titolo']}", expanded=True):
                col_l, col_r = st.columns([3, 1.5])
                with col_l:
                    with st.form(key=f"f_edit_{task_id}"):
                        new_tit = st.text_input("Titolo:", value=t_db["Titolo"])
                        new_lnk = st.text_input("Link:", value=str(t_db["Link"]) if t_db["Link"] else "")
                        
                        if new_lnk and str(new_lnk).startswith("http"):
                            st.link_button("🚀 APRI LINK", new_lnk, use_container_width=True)
                        
                        new_cnt = st.text_area("Contenuto:", value=t_db["Contenuto"], height=180)
                        
                        if st.form_submit_button("💾 SALVA MODIFICHE", use_container_width=True, type="primary"):
                            run_query("UPDATE tasks SET Titolo=?, Link=?, Contenuto=? WHERE ID=?", 
                                      (new_tit, new_lnk, new_cnt, task_id))
                            st.rerun()

                    if st.button("🗑️ ELIMINA RECORD", use_container_width=True):
                        run_query("DELETE FROM tasks WHERE ID=?", (task_id,))
                        st.rerun()

                with col_r:
                    if t_db["Foto_Bytes"]:
                        st.image(t_db["Foto_Bytes"])
                        st.download_button("📥 SCARICA FOTO", t_db["Foto_Bytes"], f"media_{task_id}.png", "image/png", use_container_width=True)
    else:
        st.info("Nessun task trovato. Inseriscine uno dalla sidebar!")

with tab2:
    st.subheader("Configurazione")
    # Tasti per pulizia massiva
    tit_del = st.text_input("Titolo da rimuovere massivamente:")
    if st.button("Togli dal DB record con questo Titolo"):
        if tit_del:
            run_query("DELETE FROM tasks WHERE Titolo = ?", (tit_del,))
            st.rerun()
