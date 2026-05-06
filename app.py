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
    try: return f"data:image/png;base64,{base64.encodebytes(image_bytes).decode()}"
    except: return None

# --- CALLBACKS (LA SOLUZIONE) ---
def save_changes(tid):
    # Recuperiamo i valori direttamente dallo stato dei widget
    new_tit = st.session_state[f"etit_{tid}"]
    new_lnk = st.session_state[f"elnk_{tid}"]
    new_cnt = st.session_state[f"ecnt_{tid}"]
    run_query("UPDATE tasks SET Titolo=?, Link=?, Contenuto=? WHERE ID=?", 
              (new_tit, new_lnk, new_cnt, tid))
    st.toast("✅ Modifiche salvate con successo!")

def delete_task(tid):
    run_query("DELETE FROM tasks WHERE ID=?", (tid,))
    if "selected_tid" in st.session_state:
        del st.session_state.selected_tid
    st.toast("🗑️ Task eliminato")

# --- CARICAMENTO DATI ---
df_task, team_list, canali_list = get_all_data()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🚀 Nuovo Piano")
    titolo_in = st.text_input("Titolo *")
    testo_in = st.text_area("Testo Post *")
    link_in = st.text_input("Link")
    foto_in = st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'])
    canali_sel = st.multiselect("Canali:", canali_list)
    data_inizio = st.date_input("Inizio", datetime.now())
    data_fine = st.date_input("Fine", datetime.now() + timedelta(days=7))
    frequenza = st.number_input("Ogni quanti giorni?", min_value=1, value=1)
    assegnati_a = st.multiselect("Assegna a:", team_list)
    
    if st.button("Genera Piano", type="primary", use_container_width=True):
        if titolo_in and testo_in:
            curr = data_inizio
            while curr <= data_fine:
                run_query('''INSERT INTO tasks (Titolo, Data_Prevista, Canali, Contenuto, Link, Foto_Nome, Foto_Bytes, Assegnato_a, Stato, Completato_da, Data_Fine) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (titolo_in, curr.strftime("%Y-%m-%d"), ", ".join(canali_sel), testo_in, link_in, 
                           foto_in.name if foto_in else "", foto_in.getvalue() if foto_in else None,
                           ", ".join(assegnati_a), "🔴 Da fare", "-", "-"))
                curr += timedelta(days=frequenza)
            st.rerun()

# --- MAIN ---
st.title("📅 Social Task Manager Pro")
tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        if 'page' not in st.session_state: st.session_state.page = 1
        per_page = 10
        total_p = math.ceil(len(df_task) / per_page)
        start = (st.session_state.page - 1) * per_page
        df_page = df_task.iloc[start:start+per_page].copy()

        df_page['Data'] = pd.to_datetime(df_page['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_page['Foto'] = df_page['Foto_Bytes'].apply(get_image_base64)
        df_page.insert(0, "📂", False)
        
        edited = st.data_editor(
            df_page[["📂", "Foto", "Titolo", "Data", "Stato"]],
            column_config={
                "📂": st.column_config.CheckboxColumn("Vedi", width="small"),
                "Foto": st.column_config.ImageColumn("Anteprima"),
            },
            disabled=["Foto", "Titolo", "Data", "Stato"],
            hide_index=True, use_container_width=True, key="main_task_editor", row_height=35
        )

        # Selezione ID
        selection = edited[edited["📂"] == True]
        if not selection.empty:
            st.session_state.selected_tid = df_page.loc[selection.index[0], "ID"]

        # Form di Modifica
        if "selected_tid" in st.session_state:
            current_task = df_task[df_task["ID"] == st.session_state.selected_tid].iloc[0]
            tid = current_task["ID"]
            
            with st.expander(f"⚙️ MODIFICA: {current_task['Titolo']}", expanded=True):
                col_l, col_r = st.columns([3, 1.5])
                with col_l:
                    # Usiamo i Key per i widget
                    st.text_input("Titolo:", value=current_task["Titolo"], key=f"etit_{tid}")
                    st.text_input("Link:", value=str(current_task["Link"]) if current_task["Link"] else "", key=f"elnk_{tid}")
                    st.text_area("Contenuto:", value=current_task["Contenuto"], key=f"ecnt_{tid}", height=150)
                    
                    c1, c2, c3 = st.columns(3)
                    # Il segreto è 'on_click'
                    c1.button("💾 SALVA", type="primary", on_click=save_changes, args=(tid,), use_container_width=True)
                    c2.button("🗑️ ELIMINA", on_click=delete_task, args=(tid,), use_container_width=True)
                    if c3.button("✖️ CHIUDI", use_container_width=True):
                        del st.session_state.selected_tid
                        st.rerun()

                with col_r:
                    if current_task["Foto_Bytes"]:
                        st.image(current_task["Foto_Bytes"])
    else:
        st.info("Archivio vuoto.")

with tab2:
    st.subheader("Configurazione")
    # ... (il resto del codice della Tab 2 rimane invariato)
    st.write("Usa la sidebar per aggiungere o la Tab 1 per gestire.")
