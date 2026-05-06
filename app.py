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
    titolo = st.text_input("Titolo *")
    testo = st.text_area("Testo Post *")
    link_input = st.text_input("Link (inizia con http://)")
    foto = st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'])
    canali_sel = st.multiselect("Canali:", canali_list)
    data_in = st.date_input("Inizio", datetime.now())
    data_fi = st.date_input("Fine", datetime.now() + timedelta(days=7))
    freq = st.number_input("Ogni quanti giorni?", min_value=1, value=1)
    assegnati = st.multiselect("Assegna a:", team_list)
    
    if st.button("Genera Piano", type="primary", use_container_width=True):
        if titolo and testo:
            curr = data_in
            while curr <= data_fi:
                run_query('''INSERT INTO tasks (Titolo, Data_Prevista, Canali, Contenuto, Link, Foto_Nome, Foto_Bytes, Assegnato_a, Stato, Completato_da, Data_Fine) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (titolo, curr.strftime("%Y-%m-%d"), ", ".join(canali_sel), testo, link_input, 
                           foto.name if foto else "", foto.getvalue() if foto else None,
                           ", ".join(assegnati), "🔴 Da fare", "-", "-"))
                curr += timedelta(days=freq)
            st.rerun()

# --- CONTENUTO PRINCIPALE ---
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
        
        # Editor Tabella
        edited = st.data_editor(
            df_page[["📂", "Foto", "Titolo", "Data", "Stato"]],
            column_config={
                "📂": st.column_config.CheckboxColumn("Vedi", width="small"),
                "Foto": st.column_config.ImageColumn("Anteprima"),
            },
            disabled=["Foto", "Titolo", "Data", "Stato"],
            hide_index=True, use_container_width=True, key="main_task_editor", row_height=35
        )

        # Navigazione Pagine
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

        # Dettagli Task selezionato
        selection = edited[edited["📂"] == True]
        if not selection.empty:
            for idx in selection.index:
                task = df_page.loc[idx]
                tid = task["ID"]
                with st.expander(f"⚙️ GESTIONE: {task['Titolo']}", expanded=True):
                    col_l, col_r = st.columns([3, 1.5])
                    with col_l:
                        raw_link = str(task["Link"]) if task["Link"] else ""
                        if raw_link.startswith("http"):
                            st.link_button("🚀 Vai al Link", raw_link, use_container_width=True)
                        
                        new_t = st.text_area("Contenuto:", value=task["Contenuto"], key=f"t_{tid}")
                        
                        b1, b2 = st.columns(2)
                        if b1.button("💾 Salva", key=f"s_{tid}", type="primary", use_container_width=True):
                            run_query("UPDATE tasks SET Contenuto = ? WHERE ID = ?", (new_t, tid))
                            st.rerun()
                        
                        # ELIMINAZIONE CORRETTA
                        if b2.button("🗑️ ELIMINA", key=f"del_{tid}", use_container_width=True):
                            run_query("DELETE FROM tasks WHERE ID = ?", (tid,))
                            st.rerun()

                    with col_r:
                        if task["Foto_Bytes"]:
                            st.image(task["Foto_Bytes"])
                            st.download_button("📥 Scarica", task["Foto_Bytes"], f"f_{tid}.png", key=f"dl_{tid}")
    else:
        st.info("Nessun task.")

with tab2:
    st.subheader("Configurazione")
    c1, c2 = st.columns(2)
    with c1:
        m_in = st.text_input("Nuovo Membro:")
        if st.button("Aggiungi Membro"):
            if m_in: run_query("INSERT OR IGNORE INTO team (nome) VALUES (?)", (m_in,))
            st.rerun()
        for m in team_list: st.text(f"• {m}")
    with c2:
        c_in = st.text_input("Nuovo Canale:")
        if st.button("Aggiungi Canale"):
            if c_in: run_query("INSERT OR IGNORE INTO canali (nome) VALUES (?)", (c_in,))
            st.rerun()
        for c in canali_list: st.text(f"• {c}")
