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

# Funzione per caricare i dati SENZA CACHE (così legge sempre il vero DB)
def get_all_data_fresh():
    with sqlite3.connect(DB_NAME) as conn:
        df_t = pd.read_sql_query("SELECT * FROM tasks ORDER BY Data_Prevista ASC", conn)
        df_team = pd.read_sql_query("SELECT nome FROM team", conn)
        df_canali = pd.read_sql_query("SELECT nome FROM canali", conn)
    t_list = df_team["nome"].tolist() if not df_team.empty else ["Membro 1"]
    c_list = df_canali["nome"].tolist() if not df_canali.empty else ["Instagram"]
    return df_t, t_list, c_list

def get_image_base64(image_bytes):
    if not image_bytes: return None
    try: return f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
    except: return None

# --- CARICAMENTO DATI ---
# Carichiamo i dati all'inizio di ogni esecuzione
df_task, team_list, canali_list = get_all_data_fresh()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🚀 Nuovo Piano")
    titolo_in = st.text_input("Titolo *", key="new_titolo")
    testo_in = st.text_area("Testo Post *", key="new_testo")
    link_in = st.text_input("Link", key="new_link")
    foto_in = st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'])
    canali_sel = st.multiselect("Canali:", canali_list)
    d_ini = st.date_input("Inizio", datetime.now())
    d_fin = st.date_input("Fine", datetime.now() + timedelta(days=7))
    freq = st.number_input("Ogni quanti giorni?", min_value=1, value=1)
    ass_a = st.multiselect("Assegna a:", team_list)
    
    if st.button("Genera Piano", type="primary", use_container_width=True):
        if titolo_in and testo_in:
            curr = d_ini
            while curr <= d_fin:
                run_query('''INSERT INTO tasks (Titolo, Data_Prevista, Canali, Contenuto, Link, Foto_Nome, Foto_Bytes, Assegnato_a, Stato, Completato_da, Data_Fine) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (titolo_in, curr.strftime("%Y-%m-%d"), ", ".join(canali_sel), testo_in, link_in, 
                           foto_in.name if foto_in else "", foto_in.getvalue() if foto_in else None,
                           ", ".join(ass_a), "🔴 Da fare", "-", "-"))
                curr += timedelta(days=freq)
            st.rerun()

# --- MAIN ---
st.title("📅 Social Task Manager Pro")
tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        # Paginazione
        per_page = 10
        total_p = math.ceil(len(df_task) / per_page)
        page = st.number_input("Pagina", min_value=1, max_value=total_p, step=1, key="page_nav")
        start = (page - 1) * per_page
        df_page = df_task.iloc[start:start+per_page].copy()

        df_page['Data'] = pd.to_datetime(df_page['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_page['Foto'] = df_page['Foto_Bytes'].apply(get_image_base64)
        df_page.insert(0, "📂", False)
        
        # Editor per selezionare il record
        edited = st.data_editor(
            df_page[["📂", "Foto", "Titolo", "Data", "Stato"]],
            column_config={"📂": st.column_config.CheckboxColumn("Vedi", width="small"), "Foto": st.column_config.ImageColumn("Anteprima")},
            disabled=["Foto", "Titolo", "Data", "Stato"],
            hide_index=True, use_container_width=True, key="editor_v1"
        )

        # Logica di modifica
        selected_rows = edited[edited["📂"] == True]
        if not selected_rows.empty:
            idx = selected_rows.index[0]
            task_id = df_page.loc[idx, "ID"]
            # IMPORTANTE: rileggiamo il singolo record dal DB per essere sicuri dei dati
            with sqlite3.connect(DB_NAME) as conn:
                task_db = pd.read_sql_query("SELECT * FROM tasks WHERE ID=?", conn, params=(int(task_id),)).iloc[0]

            with st.expander(f"⚙️ MODIFICA RECORD ID: {task_id}", expanded=True):
                # Usiamo form per raggruppare l'invio dei dati
                with st.form(key=f"form_edit_{task_id}"):
                    new_tit = st.text_input("Titolo:", value=task_db["Titolo"])
                    new_lnk = st.text_input("Link:", value=str(task_db["Link"]) if task_db["Link"] else "")
                    new_cnt = st.text_area("Contenuto:", value=task_db["Contenuto"], height=150)
                    
                    col_btn1, col_btn2 = st.columns(2)
                    submit = col_btn1.form_submit_button("💾 SALVA MODIFICHE", use_container_width=True, type="primary")
                    delete = col_btn2.form_submit_button("🗑️ ELIMINA RECORD", use_container_width=True)

                    if submit:
                        run_query("UPDATE tasks SET Titolo=?, Link=?, Contenuto=? WHERE ID=?", 
                                  (new_tit, new_lnk, new_cnt, task_id))
                        st.success("Database aggiornato!")
                        st.rerun() # Forza il ricaricamento totale per vedere i nuovi dati
                    
                    if delete:
                        run_query("DELETE FROM tasks WHERE ID=?", (task_id,))
                        st.warning("Record eliminato!")
                        st.rerun()
    else:
        st.info("Nessun task presente.")

with tab2:
    st.subheader("Configurazione")
    tit_del = st.text_input("Titolo da rimuovere massivamente:")
    if st.button("Esegui Pulizia Massiva"):
        if tit_del:
            run_query("DELETE FROM tasks WHERE Titolo = ?", (tit_del,))
            st.rerun()
