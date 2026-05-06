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

def get_all_data():
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

# --- CALLBACKS MIGLIORATI ---
def save_changes(tid):
    # Leggiamo i valori dai widget usando le chiavi univoche
    new_tit = st.session_state[f"etit_{tid}"]
    new_lnk = st.session_state[f"elnk_{tid}"]
    new_cnt = st.session_state[f"ecnt_{tid}"]
    
    # Eseguiamo l'aggiornamento nel database
    run_query("UPDATE tasks SET Titolo=?, Link=?, Contenuto=? WHERE ID=?", 
              (new_tit, new_lnk, new_cnt, tid))
    
    # FORZIAMO il ricaricamento dei dati globali prima del prossimo ciclo
    st.session_state["force_reload"] = True
    st.toast(f"✅ Record {tid} salvato correttamente nel DB!")

def delete_task(tid):
    run_query("DELETE FROM tasks WHERE ID=?", (tid,))
    if "selected_tid" in st.session_state:
        del st.session_state.selected_tid
    st.session_state["force_reload"] = True
    st.toast("🗑️ Task rimosso.")

# --- GESTIONE DATI (RELOAD-AWARE) ---
if "force_reload" in st.session_state or "df_task" not in st.session_state:
    df_task, team_list, canali_list = get_all_data()
    st.session_state.df_task = df_task
    st.session_state.team_list = team_list
    st.session_state.canali_list = canali_list
    if "force_reload" in st.session_state:
        del st.session_state["force_reload"]
else:
    df_task = st.session_state.df_task
    team_list = st.session_state.team_list
    canali_list = st.session_state.canali_list

# --- SIDEBAR ---
with st.sidebar:
    st.header("🚀 Nuovo Piano")
    titolo_in = st.text_input("Titolo *")
    testo_in = st.text_area("Testo Post *")
    link_in = st.text_input("Link (https://...)")
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
            st.session_state["force_reload"] = True
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

        df_page['Data'] = pd.to_datetime(df_page['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_page['Foto'] = df_page['Foto_Bytes'].apply(get_image_base64)
        df_page.insert(0, "📂", False)
        
        # Tabella editor
        edited = st.data_editor(
            df_page[["📂", "Foto", "Titolo", "Data", "Stato"]],
            column_config={
                "📂": st.column_config.CheckboxColumn("Vedi", width="small"),
                "Foto": st.column_config.ImageColumn("Anteprima"),
            },
            disabled=["Foto", "Titolo", "Data", "Stato"],
            hide_index=True, use_container_width=True, key="main_task_editor", row_height=35
        )

        # Selezione persistente
        selection = edited[edited["📂"] == True]
        if not selection.empty:
            st.session_state.selected_tid = df_page.loc[selection.index[0], "ID"]

        if "selected_tid" in st.session_state:
            # Recuperiamo i dati freschi dal DataFrame ricaricato
            task_res = df_task[df_task["ID"] == st.session_state.selected_tid]
            if not task_res.empty:
                current_task = task_res.iloc[0]
                tid = current_task["ID"]
                
                with st.expander(f"⚙️ MODIFICA: {current_task['Titolo']}", expanded=True):
                    cl, cr = st.columns([3, 1.5])
                    with cl:
                        # Widget con chiavi univoche
                        st.text_input("Titolo:", value=current_task["Titolo"], key=f"etit_{tid}")
                        st.text_input("Link:", value=str(current_task["Link"]) if current_task["Link"] else "", key=f"elnk_{tid}")
                        st.text_area("Contenuto:", value=current_task["Contenuto"], key=f"ecnt_{tid}", height=150)
                        
                        c1, c2, c3 = st.columns(3)
                        # Il salvataggio chiama il callback che aggiorna il DB e forza il reload
                        c1.button("💾 SALVA", type="primary", on_click=save_changes, args=(tid,), use_container_width=True)
                        c2.button("🗑️ ELIMINA", on_click=delete_task, args=(tid,), use_container_width=True)
                        if c3.button("✖️ CHIUDI", use_container_width=True):
                            del st.session_state.selected_tid
                            st.rerun()
                    with cr:
                        if current_task["Foto_Bytes"]:
                            st.image(current_task["Foto_Bytes"])
    else:
        st.info("Nessun task.")

with tab2:
    st.subheader("Configurazione")
    # Tasto pulizia massiva aggiornato per forzare il ricaricamento
    tit_del = st.text_input("Titolo da rimuovere massivamente:")
    if st.button("Togli dal DB record con questo Titolo", type="secondary"):
        if tit_del:
            run_query("DELETE FROM tasks WHERE Titolo = ?", (tit_del,))
            st.session_state["force_reload"] = True
            st.rerun()
