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

df_task, team_list, canali_list = get_all_data()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🚀 Nuovo Piano")
    titolo_in = st.text_input("Titolo *")
    testo_in = st.text_area("Testo Post *")
    link_in = st.text_input("Link (es. https://...)")
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

# --- CONTENUTO PRINCIPALE ---
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

        # Navigazione
        cp1, cp2, cp3, cp4, cp5 = st.columns([2, 1, 1, 1, 2])
        with cp2:
            if st.button("❮", disabled=(st.session_state.page == 1)):
                st.session_state.page -= 1
                st.rerun()
        with cp3:
            st.markdown(f"<div style='text-align: center; font-weight: bold;'>{st.session_state.page}</div>", unsafe_allow_html=True)
        with cp4:
            if st.button("❯", disabled=(st.session_state.page == total_p)):
                st.session_state.page += 1
                st.rerun()

        # LOGICA DI SELEZIONE PERSISTENTE
        selection = edited[edited["📂"] == True]
        if not selection.empty:
            # Salviamo l'ID dell'ultima riga selezionata
            st.session_state.selected_tid = df_page.loc[selection.index[0], "ID"]

        # Se abbiamo un ID selezionato, mostriamo i dettagli
        if "selected_tid" in st.session_state:
            # Recuperiamo i dati aggiornati del task specifico
            task_data = df_task[df_task["ID"] == st.session_state.selected_tid]
            
            if not task_data.empty:
                task = task_data.iloc[0]
                tid = task["ID"]
                
                with st.expander(f"⚙️ GESTIONE: {task['Titolo']}", expanded=True):
                    col_l, col_r = st.columns([3, 1.5])
                    with col_l:
                        # Campi di input
                        new_tit = st.text_input("Titolo:", value=task["Titolo"], key=f"etit_{tid}")
                        new_lnk = st.text_input("Link:", value=str(task["Link"]) if task["Link"] else "", key=f"elnk_{tid}")
                        new_cnt = st.text_area("Contenuto:", value=task["Contenuto"], key=f"ecnt_{tid}", height=150)
                        
                        b1, b2, b3 = st.columns([1, 1, 1])
                        
                        if b1.button("💾 SALVA", type="primary", use_container_width=True):
                            run_query("UPDATE tasks SET Titolo=?, Link=?, Contenuto=? WHERE ID=?", 
                                      (new_tit, new_lnk, new_cnt, tid))
                            st.success("Modifiche salvate!")
                            st.rerun()
                        
                        if b2.button("🗑️ ELIMINA", use_container_width=True):
                            run_query("DELETE FROM tasks WHERE ID=?", (tid,))
                            del st.session_state.selected_tid
                            st.rerun()
                            
                        if b3.button("✖️ CHIUDI", use_container_width=True):
                            del st.session_state.selected_tid
                            st.rerun()

                    with col_r:
                        if task["Foto_Bytes"]:
                            st.image(task["Foto_Bytes"])
    else:
        st.info("Nessun task in archivio.")

with tab2:
    st.subheader("Configurazione Team e Canali")
    cl1, cl2 = st.columns(2)
    with cl1:
        m_in = st.text_input("Nuovo Membro:")
        if st.button("Aggiungi Membro"):
            if m_in: run_query("INSERT OR IGNORE INTO team (nome) VALUES (?)", (m_in,))
            st.rerun()
        for m in team_list: st.text(f"• {m}")
    with cl2:
        c_in = st.text_input("Nuovo Canale:")
        if st.button("Aggiungi Canale"):
            if c_in: run_query("INSERT OR IGNORE INTO canali (nome) VALUES (?)", (c_in,))
            st.rerun()
        for c in canali_list: st.text(f"• {c}")

    st.divider()
    st.subheader("🗑️ Pulizia Massiva")
    tit_del = st.text_input("Titolo esatto da rimuovere:")
    if st.button("Togli dal DB record con questo Titolo", use_container_width=True):
        if tit_del:
            run_query("DELETE FROM tasks WHERE Titolo = ?", (tit_del,))
            st.rerun()
