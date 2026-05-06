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

# Caricamento dati
df_task, team_list, canali_list = get_all_data_fresh()

# --- SIDEBAR (Invariata) ---
with st.sidebar:
    st.header("🚀 Nuovo Piano")
    titolo_in = st.text_input("Titolo *")
    testo_in = st.text_area("Testo Post *")
    link_in = st.text_input("Link")
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
        # Paginazione (semplificata per stabilità)
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
            column_config={"📂": st.column_config.CheckboxColumn("Vedi", width="small"), "Foto": st.column_config.ImageColumn("Anteprima")},
            disabled=["Foto", "Titolo", "Data", "Stato"],
            hide_index=True, use_container_width=True, key="editor_main"
        )

        selected_rows = edited[edited["📂"] == True]
        if not selected_rows.empty:
            idx = selected_rows.index[0]
            task_id = df_page.loc[idx, "ID"]
            
            # Recupero dati freschi del record
            with sqlite3.connect(DB_NAME) as conn:
                task_db = pd.read_sql_query("SELECT * FROM tasks WHERE ID=?", conn, params=(int(task_id),)).iloc[0]

            with st.expander(f"⚙️ GESTIONE RECORD: {task_db['Titolo']}", expanded=True):
                col_left, col_right = st.columns([3, 1.5])
                
                with col_left:
                    # FORM DI MODIFICA
                    with st.form(key=f"form_v3_{task_id}"):
                        new_tit = st.text_input("Titolo:", value=task_db["Titolo"])
                        new_lnk = st.text_input("Link:", value=str(task_db["Link"]) if task_db["Link"] else "")
                        new_cnt = st.text_area("Contenuto:", value=task_db["Contenuto"], height=180)
                        
                        btn_save = st.form_submit_button("💾 SALVA MODIFICHE", use_container_width=True, type="primary")
                        
                        if btn_save:
                            run_query("UPDATE tasks SET Titolo=?, Link=?, Contenuto=? WHERE ID=?", 
                                      (new_tit, new_lnk, new_cnt, task_id))
                            st.rerun()

                    # Tasti Azione Fuori dal Form
                    st.divider()
                    c1, c2 = st.columns(2)
                    if task_db["Link"] and str(task_db["Link"]).startswith("http"):
                        c1.link_button("🚀 APRI LINK", task_db["Link"], use_container_width=True)
                    
                    if c2.button("🗑️ ELIMINA RECORD", use_container_width=True):
                        run_query("DELETE FROM tasks WHERE ID=?", (task_id,))
                        st.rerun()

                with col_right:
                    st.write("**Anteprima Media:**")
                    if task_db["Foto_Bytes"]:
                        st.image(task_db["Foto_Bytes"])
                        st.download_button(
                            label="📥 SCARICA FOTO",
                            data=task_db["Foto_Bytes"],
                            file_name=f"post_{task_id}.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    else:
                        st.info("Nessuna immagine.")

        # Navigazione pagine
        st.write(f"Pagina {st.session_state.page} di {total_p}")
        cp1, cp2 = st.columns([1, 1])
        if cp1.button("❮ Precedente") and st.session_state.page > 1:
            st.session_state.page -= 1
            st.rerun()
        if cp2.button("Successiva ❯") and st.session_state.page < total_p:
            st.session_state.page += 1
            st.rerun()

with tab2:
    st.subheader("Configurazione Canali e Team")
    # ... (Parte della tab2 lasciata invariata per brevità)
    st.info("Usa la sidebar per nuovi inserimenti o la Tab 1 per modificare.")
