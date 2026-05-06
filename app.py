import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import base64

st.set_page_config(page_title="Social Task Manager Pro", layout="wide", page_icon="📅")

# --- FUNZIONI DI SUPPORTO ---
def get_image_base64(image_bytes):
    if not image_bytes: return None
    try:
        base64_str = base64.b64encode(image_bytes).decode()
        return f"data:image/png;base64,{base64_str}"
    except: return None

# --- FUNZIONI DATABASE ---
DB_NAME = "social_tasks.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # AGGIORNATO: Aggiunta colonna Link
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                  Titolo TEXT, Data_Prevista TEXT, Canali TEXT, Contenuto TEXT, 
                  Link TEXT, Foto_Nome TEXT, Foto_Bytes BLOB, Assegnato_a TEXT, 
                  Stato TEXT, Completato_da TEXT, Data_Fine TEXT)''')
    
    # Migrazione dinamica per aggiungere colonne mancanti (Titolo e Link)
    c.execute("PRAGMA table_info(tasks)")
    columns = [column[1] for column in c.fetchall()]
    if 'Titolo' not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN Titolo TEXT DEFAULT 'Senza Titolo'")
    if 'Link' not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN Link TEXT")
        
    c.execute('CREATE TABLE IF NOT EXISTS team (nome TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS canali (nome TEXT UNIQUE)')
    conn.commit()
    conn.close()

def run_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

init_db()

# --- CARICAMENTO DATI ---
def get_all_data():
    conn = sqlite3.connect(DB_NAME)
    df_t = pd.read_sql_query("SELECT * FROM tasks ORDER BY Data_Prevista ASC", conn)
    list_t = pd.read_sql_query("SELECT nome FROM team", conn)["nome"].tolist() if not pd.read_sql_query("SELECT count(*) FROM team", conn).iloc[0,0] == 0 else ["Marco", "Giulia"]
    list_c = pd.read_sql_query("SELECT nome FROM canali", conn)["nome"].tolist() if not pd.read_sql_query("SELECT count(*) FROM canali", conn).iloc[0,0] == 0 else ["Instagram", "Facebook"]
    conn.close()
    return df_t, list_t, list_c

df_task, team_list, canali_list = get_all_data()

# --- LOGICA GENERAZIONE ---
def genera_piano():
    if not st.session_state.input_titolo or not st.session_state.input_testo:
        st.error("Compila i campi obbligatori!")
        return

    titolo = st.session_state.input_titolo
    testo = st.session_state.input_testo
    link = st.session_state.input_link # Nuovo campo
    inizio = st.session_state.input_data_inizio
    fine = st.session_state.input_data_fine
    frequenza = st.session_state.input_frequenza
    assegnati = ", ".join(st.session_state.input_assegnati)
    canali = ", ".join(st.session_state.input_canali)
    foto = st.session_state.input_foto
    
    foto_bytes = foto.getvalue() if foto else None
    foto_nome = foto.name if foto else ""
    
    conn = sqlite3.connect(DB_NAME)
    curr_date = inizio
    while curr_date <= fine:
        conn.execute('''INSERT INTO tasks 
            (Titolo, Data_Prevista, Canali, Contenuto, Link, Foto_Nome, Foto_Bytes, Assegnato_a, Stato, Completato_da, Data_Fine) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (titolo, curr_date.strftime("%Y-%m-%d"), canali, testo, link, foto_nome, foto_bytes, assegnati, "🔴 Da fare", "-", "-"))
        curr_date += timedelta(days=frequenza)
    conn.commit()
    conn.close()
    st.rerun()

# --- INTERFACCIA ---
st.title("📅 Social Manager Pro")

with st.sidebar:
    st.header("🚀 Nuovo Piano")
    st.text_input("Titolo *", key="input_titolo")
    st.text_area("Testo Post *", key="input_testo")
    st.text_input("Link (URL)", key="input_link", placeholder="https://...") # Input Link
    st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'], key="input_foto")
    st.multiselect("Canali:", canali_list, key="input_canali")
    st.date_input("Inizio", datetime.now(), key="input_data_inizio")
    st.date_input("Fine", datetime.now() + timedelta(days=7), key="input_data_fine")
    st.number_input("Frequenza (gg)", min_value=1, value=1, key="input_frequenza")
    st.multiselect("Responsabili:", team_list, key="input_assegnati")
    if st.button("Genera Piano", type="primary", use_container_width=True):
        genera_piano()

tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with tab1:
    if not df_task.empty:
        df_vis = df_task.copy()
        df_vis['Data_Prevista'] = pd.to_datetime(df_vis['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_vis['Anteprima'] = df_vis['Foto_Bytes'].apply(get_image_base64)
        df_vis.insert(0, "Sel.", False)
        
        # AGGIORNATO: Aggiunta colonna Link nella visualizzazione
        col_view = ["Sel.", "Anteprima", "Titolo", "Link", "Data_Prevista", "Assegnato_a", "Stato"]
        
        edited = st.data_editor(
            df_vis[col_view],
            column_config={
                "Sel.": st.column_config.CheckboxColumn("", width="small"),
                "Anteprima": st.column_config.ImageColumn("Foto"),
                "Titolo": st.column_config.TextColumn("Titolo", width="medium"),
                "Link": st.column_config.LinkColumn("Link Risorsa", display_text="Apri Link"), # Rende il link cliccabile
                "Assegnato_a": "Responsabile",
                "Data_Prevista": "Scadenza"
            },
            disabled=[c for c in col_view if c != "Sel."],
            hide_index=True, use_container_width=True, key="editor_main", row_height=70
        )
        
        selected_rows = edited[edited["Sel."] == True].index.tolist()
        
        if selected_rows:
            st.divider()
            for idx in selected_rows:
                task = df_task.iloc[idx]
                tid = task["ID"]
                
                with st.expander(f"📝 Dettaglio: {task['Titolo']} ({task['Data_Prevista']})", expanded=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        # Permetti modifica Link nel dettaglio
                        new_link = st.text_input("Link:", task["Link"], key=f"link_{tid}")
                        if new_link != task["Link"]:
                            run_query("UPDATE tasks SET Link = ? WHERE ID = ?", (new_link, tid))
                            
                        new_c = st.text_area("Testo:", task["Contenuto"], key=f"c_{tid}", height=100)
                        if new_c != task["Contenuto"]:
                            run_query("UPDATE tasks SET Contenuto = ? WHERE ID = ?", (new_c, tid))
                    with c2:
                        if task["Foto_Bytes"]: st.image(task["Foto_Bytes"])
                    
                    st.divider()
                    ca1, ca2, ca3 = st.columns([2,2,1])
                    if task["Stato"] != "🟢 Completato":
                        user = ca1.selectbox("Eseguito da:", team_list, key=f"u_{tid}")
                        if ca2.button("Segna come Fatto", key=f"f_{tid}", use_container_width=True):
                            ts = datetime.now().strftime("%d/%m %H:%M")
                            run_query("UPDATE tasks SET Stato='🟢 Completato', Completato_da=?, Data_Fine=? WHERE ID=?", (user, ts, tid))
                            st.rerun()
                    else:
                        ca1.success(f"Fatto da {task['Completato_da']}")
                    
                    if ca3.button("Elimina", key=f"d_{tid}", use_container_width=True):
                        run_query("DELETE FROM tasks WHERE ID = ?", (tid,))
                        st.rerun()
    else:
        st.info("Nessun task programmato.")

with tab2:
    st.subheader("⚙️ Configurazione")
    st.write("Configurazione database e tabelle di supporto attiva.")
