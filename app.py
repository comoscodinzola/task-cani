import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import base64

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Social Task Manager Pro", layout="wide", page_icon="📅")

DB_NAME = "social_tasks.db"

# --- FUNZIONI DI SUPPORTO ---
def get_image_base64(image_bytes):
    if not image_bytes: return None
    try:
        base64_str = base64.b64encode(image_bytes).decode()
        return f"data:image/png;base64,{base64_str}"
    except: return None

# --- GESTIONE DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                  Titolo TEXT, Data_Prevista TEXT, Canali TEXT, Contenuto TEXT, 
                  Link TEXT, Foto_Nome TEXT, Foto_Bytes BLOB, Assegnato_a TEXT, 
                  Stato TEXT, Completato_da TEXT, Data_Fine TEXT)''')
    
    c.execute("PRAGMA table_info(tasks)")
    existing_cols = [col[1] for col in c.fetchall()]
    migrazioni = [("Titolo", "TEXT DEFAULT 'Senza Titolo'"), ("Link", "TEXT"), ("Assegnato_a", "TEXT")]
    for col_name, col_type in migrazioni:
        if col_name not in existing_cols:
            try:
                c.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
            except: pass
            
    c.execute('CREATE TABLE IF NOT EXISTS team (nome TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS canali (nome TEXT UNIQUE)')
    conn.commit()
    conn.close()

def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()

init_db()

# --- CARICAMENTO DATI ---
def get_all_data():
    with sqlite3.connect(DB_NAME) as conn:
        df_t = pd.read_sql_query("SELECT * FROM tasks ORDER BY Data_Prevista ASC", conn)
        df_team = pd.read_sql_query("SELECT nome FROM team", conn)
        df_canali = pd.read_sql_query("SELECT nome FROM canali", conn)
    list_t = df_team["nome"].tolist() if not df_team.empty else ["Marco", "Giulia"]
    list_c = df_canali["nome"].tolist() if not df_canali.empty else ["Instagram", "Facebook", "TikTok"]
    return df_t, list_t, list_c

df_task, team_list, canali_list = get_all_data()

# --- INTERFACCIA ---
st.title("📅 Social Task Manager Pro")

with st.sidebar:
    st.header("🚀 Nuovo Piano")
    t_titolo = st.text_input("Titolo *")
    t_testo = st.text_area("Testo Post *")
    t_link = st.text_input("Link Risorsa (URL)")
    t_foto = st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'])
    if st.button("Genera Task", type="primary", use_container_width=True):
        if t_titolo and t_testo:
            run_query('''INSERT INTO tasks (Titolo, Data_Prevista, Contenuto, Link, Foto_Nome, Foto_Bytes, Stato) 
                         VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                      (t_titolo, datetime.now().strftime("%Y-%m-%d"), t_testo, t_link, 
                       t_foto.name if t_foto else "", t_foto.getvalue() if t_foto else None, "🔴 Da fare"))
            st.rerun()

tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        # Prepariamo il dataframe per la visualizzazione
        df_vis = df_task.copy()
        df_vis['Anteprima'] = df_vis['Foto_Bytes'].apply(get_image_base64)
        df_vis.insert(0, "📂", False)
        df_vis.insert(len(df_vis.columns), "🗑️", False)

        # Editor della tabella
        edited_df = st.data_editor(
            df_vis[["📂", "Anteprima", "Titolo", "Link", "Data_Prevista", "Stato", "🗑️"]],
            column_config={
                "📂": st.column_config.CheckboxColumn("Dett.", width="small"),
                "Anteprima": st.column_config.ImageColumn("Foto"),
                "Link": st.column_config.LinkColumn("Link"),
                "🗑️": st.column_config.CheckboxColumn("Elimina", width="small"),
            },
            disabled=["Anteprima", "Titolo", "Link", "Data_Prevista", "Stato"],
            hide_index=True, use_container_width=True, key="task_editor"
        )

        # GESTIONE ELIMINAZIONE (Il segreto è controllare i dati editati)
        indices_to_delete = edited_df[edited_df["🗑️"] == True].index.tolist()
        
        if indices_to_delete:
            st.warning(f"Hai selezionato {len(indices_to_delete)} task.")
            if st.button("CONFERMA ELIMINAZIONE", type="primary"):
                for idx in indices_to_delete:
                    # Recuperiamo l'ID reale dal dataframe originale usando l'indice della riga
                    real_id = df_task.iloc[idx]["ID"]
                    run_query("DELETE FROM tasks WHERE ID = ?", (real_id,))
                st.rerun()

        # GESTIONE DETTAGLI
        indices_to_edit = edited_df[edited_df["📂"] == True].index.tolist()
        for idx in indices_to_edit:
            task = df_task.iloc[idx]
            tid = task["ID"]
            with st.expander(f"MODIFICA: {task['Titolo']}", expanded=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    new_link = st.text_input("Link:", value=task["Link"] if task["Link"] else "", key=f"l_{tid}")
                    if new_link: st.link_button("🚀 Vai al Link", new_link)
                    
                    new_txt = st.text_area("Testo:", value=task["Contenuto"], key=f"t_{tid}", height=150)
                    if st.button("Salva", key=f"s_{tid}"):
                        run_query("UPDATE tasks SET Contenuto = ?, Link = ? WHERE ID = ?", (new_txt, new_link, tid))
                        st.rerun()
                with c2:
                    if task["Foto_Bytes"]:
                        st.image(task["Foto_Bytes"])
                        st.download_button("💾 Scarica", task["Foto_Bytes"], f"{tid}.png", key=f"d_{tid}")
    else:
        st.info("Nessun task.")

with tab2:
    st.subheader("Configurazione")
    # ... (Il resto rimane invariato)
