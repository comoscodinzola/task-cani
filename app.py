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

# --- CALLBACK PER ELIMINAZIONE SICURA ---
def elimina_task_callback(task_id):
    run_query("DELETE FROM tasks WHERE ID = ?", (task_id,))
    st.success(f"Task {task_id} eliminato con successo!")
    # Non serve rerun() qui, la callback lo gestisce nativamente

def get_all_data():
    with sqlite3.connect(DB_NAME) as conn:
        df_t = pd.read_sql_query("SELECT * FROM tasks ORDER BY Data_Prevista ASC", conn)
        df_team = pd.read_sql_query("SELECT nome FROM team", conn)
        df_canali = pd.read_sql_query("SELECT nome FROM canali", conn)
    return df_t, df_team["nome"].tolist(), df_canali["nome"].tolist()

def get_image_base64(image_bytes):
    if not image_bytes: return None
    try: return f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
    except: return None

df_task, team_list, canali_list = get_all_data()

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
        
        edited = st.data_editor(
            df_page[["📂", "Foto", "Titolo", "Link", "Data", "Stato"]],
            column_config={
                "📂": st.column_config.CheckboxColumn("Vedi", width="small"),
                "Foto": st.column_config.ImageColumn("Anteprima"),
                "Link": st.column_config.LinkColumn("Link"),
            },
            disabled=["Foto", "Titolo", "Link", "Data", "Stato"],
            hide_index=True, use_container_width=True, key="main_task_editor", row_height=35
        )

        # Controlli paginazione
        cp1, cp2, cp3, cp4, cp5 = st.columns([2, 1, 1, 1, 2])
        with cp2:
            if st.button("❮", disabled=(st.session_state.page == 1)):
                st.session_state.page -= 1
                st.rerun()
        with cp3:
            st.markdown(f"<div style='text-align: center; background-color: #f0fdf4; border: 1px solid #dcfce7; border-radius: 50%; width: 35px; height: 35px; line-height: 35px; margin: auto; font-weight: bold; color: #16a34a;'>{st.session_state.page}</div>", unsafe_allow_html=True)
        with cp4:
            if st.button("❯", disabled=(st.session_state.page == total_p)):
                st.session_state.page += 1
                st.rerun()

        # Dettagli e Eliminazione
        selection = edited[edited["📂"] == True]
        if not selection.empty:
            for idx in selection.index:
                task = df_page.loc[idx]
                tid = task["ID"]
                with st.expander(f"⚙️ GESTIONE: {task['Titolo']}", expanded=True):
                    col_l, col_r = st.columns([3, 1.5])
                    with col_l:
                        # Tasti Azione
                        b_col1, b_col2 = st.columns(2)
                        # IL FIX: Usiamo on_click e passiamo l'ID tramite args
                        b_col2.button("🗑️ ELIMINA DEFINITIVAMENTE", 
                                      key=f"del_btn_{tid}", 
                                      on_click=elimina_task_callback, 
                                      args=(tid,),
                                      type="secondary",
                                      use_container_width=True)
                        
                        # Link e Testo
                        l_val = task["Link"] if task["Link"] and str(task["Link"]) != "None" else ""
                        st.text_input("Link:", value=l_val, key=f"l_{tid}", disabled=True)
                        if l_val: st.link_button("🚀 Vai al Link", l_val)
                        st.text_area("Contenuto:", value=task["Contenuto"], key=f"t_{tid}", height=100)

                    with col_r:
                        if task["Foto_Bytes"]:
                            st.image(task["Foto_Bytes"])
                            st.download_button("📥 Scarica", task["Foto_Bytes"], f"f_{tid}.png", key=f"dl_{tid}")

    else:
        st.info("Nessun task.")

with tab2:
    st.subheader("Configurazione")
    # ... (il codice delle liste corretto prima)
    st.write("**Team attuale:**")
    for m in team_list: st.text(f"• {m}")
    st.write("**Canali attuali:**")
    for c in canali_list: st.text(f"• {c}")
