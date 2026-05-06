import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import base64

# Configurazione pagina (deve essere la prima istruzione Streamlit)
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
    # Creazione tabella principale con tutti i campi necessari
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                  Titolo TEXT, Data_Prevista TEXT, Canali TEXT, Contenuto TEXT, 
                  Link TEXT, Foto_Nome TEXT, Foto_Bytes BLOB, Assegnato_a TEXT, 
                  Stato TEXT, Completato_da TEXT, Data_Fine TEXT)''')
    
    # Migrazioni sicure (aggiungono colonne solo se mancano)
    columns_to_add = [
        ("Titolo", "TEXT DEFAULT 'Senza Titolo'"),
        ("Link", "TEXT"),
        ("Assegnato_a", "TEXT")
    ]
    
    c.execute("PRAGMA table_info(tasks)")
    existing_columns = [col[1] for col in c.fetchall()]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            try:
                c.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
            except:
                pass

    c.execute('CREATE TABLE IF NOT EXISTS team (nome TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS canali (nome TEXT UNIQUE)')
    conn.commit()
    conn.close()

def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()

# Inizializzazione
init_db()

# --- CARICAMENTO DATI ---
def get_all_data():
    conn = sqlite3.connect(DB_NAME)
    df_t = pd.read_sql_query("SELECT * FROM tasks ORDER BY Data_Prevista ASC", conn)
    df_team = pd.read_sql_query("SELECT nome FROM team", conn)
    df_canali = pd.read_sql_query("SELECT nome FROM canali", conn)
    conn.close()
    
    list_t = df_team["nome"].tolist() if not df_team.empty else ["Marco", "Giulia"]
    list_c = df_canali["nome"].tolist() if not df_canali.empty else ["Instagram", "Facebook", "LinkedIn"]
    return df_t, list_t, list_c

# Chiamata sicura ai dati
try:
    df_task, team_list, canali_list = get_all_data()
except:
    st.error("Errore nel caricamento dei dati. Prova a ricaricare la pagina.")
    st.stop()

# --- LOGICA GENERAZIONE ---
def genera_piano():
    if not st.session_state.input_titolo or not st.session_state.input_testo:
        st.error("Inserisci almeno Titolo e Testo!")
        return

    titolo = st.session_state.input_titolo
    testo = st.session_state.input_testo
    link = st.session_state.input_link
    inizio = st.session_state.input_data_inizio
    fine = st.session_state.input_data_fine
    frequenza = st.session_state.input_frequenza
    assegnati = ", ".join(st.session_state.input_assegnati)
    canali = ", ".join(st.session_state.input_canali)
    foto = st.session_state.input_foto
    
    foto_bytes = foto.getvalue() if foto else None
    foto_nome = foto.name if foto else ""
    
    with sqlite3.connect(DB_NAME) as conn:
        curr_date = inizio
        while curr_date <= fine:
            conn.execute('''INSERT INTO tasks 
                (Titolo, Data_Prevista, Canali, Contenuto, Link, Foto_Nome, Foto_Bytes, Assegnato_a, Stato, Completato_da, Data_Fine) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (titolo, curr_date.strftime("%Y-%m-%d"), canali, testo, link, foto_nome, foto_bytes, assegnati, "🔴 Da fare", "-", "-"))
            curr_date += timedelta(days=frequenza)
    st.success("Piano generato!")
    st.rerun()

# --- INTERFACCIA ---
st.title("📅 Social Task Manager Pro")

# Sidebar
with st.sidebar:
    st.header("🚀 Nuovo Piano")
    st.text_input("Titolo *", key="input_titolo")
    st.text_area("Testo Post *", key="input_testo")
    st.text_input("Link (URL)", key="input_link")
    st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'], key="input_foto")
    st.multiselect("Canali:", canali_list, key="input_canali")
    st.date_input("Inizio", datetime.now(), key="input_data_inizio")
    st.date_input("Fine", datetime.now() + timedelta(days=7), key="input_data_fine")
    st.number_input("Ogni quanti giorni?", min_value=1, value=1, key="input_frequenza")
    st.multiselect("Assegna a:", team_list, key="input_assegnati")
    if st.button("Genera Piano", type="primary", use_container_width=True):
        genera_piano()

# Tabs
tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        df_vis = df_task.copy()
        df_vis['Data_Prevista'] = pd.to_datetime(df_vis['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_vis['Anteprima'] = df_vis['Foto_Bytes'].apply(get_image_base64)
        df_vis.insert(0, "Sel.", False)
        
        # Colonne da mostrare
        col_view = ["Sel.", "Anteprima", "Titolo", "Link", "Data_Prevista", "Assegnato_a", "Stato"]
        
        edited = st.data_editor(
            df_vis[col_view],
            column_config={
                "Sel.": st.column_config.CheckboxColumn("", width="small"),
                "Anteprima": st.column_config.ImageColumn("Foto"),
                "Titolo": st.column_config.TextColumn("Titolo", width="medium"),
                "Link": st.column_config.LinkColumn("Link", display_text="Apri"),
                "Assegnato_a": "Responsabile",
                "Data_Prevista": "Scadenza"
            },
            disabled=[c for c in col_view if c != "Sel."],
            hide_index=True, use_container_width=True, key="editor_v1", row_height=70
        )
        
        selected_indices = edited[edited["Sel."] == True].index.tolist()
        
        if selected_indices:
            st.divider()
            for idx in selected_indices:
                task = df_task.iloc[idx]
                tid = task["ID"]
                with st.expander(f"Dettaglio: {task['Titolo']}", expanded=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        new_txt = st.text_area("Modifica Testo:", task["Contenuto"], key=f"t_{tid}")
                        if st.button("Salva Modifica", key=f"s_{tid}"):
                            run_query("UPDATE tasks SET Contenuto = ? WHERE ID = ?", (new_txt, tid))
                            st.rerun()
                    with c2:
                        if task["Foto_Bytes"]: st.image(task["Foto_Bytes"])
                    
                    if st.button("🗑️ Elimina Task", key=f"del_{tid}"):
                        run_query("DELETE FROM tasks WHERE ID = ?", (tid,))
                        st.rerun()
    else:
        st.info("Nessun task presente. Usa la barra laterale per crearne uno!")

with tab2:
    st.write("Gestione configurazione (Team e Canali)")
    # Se la pagina era vuota per errori di DB, questo tab apparirà dopo il reset
