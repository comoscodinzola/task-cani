import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Social Task Manager DB", layout="wide", page_icon="📅")

# --- FUNZIONI DATABASE SQLITE ---
DB_NAME = "social_tasks.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabella Task
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                  Data_Prevista TEXT, Canali TEXT, Contenuto TEXT, 
                  Foto_Nome TEXT, Foto_Bytes BLOB, Assegnato_a TEXT, 
                  Stato TEXT, Completato_da TEXT, Data_Fine TEXT)''')
    # Tabelle Impostazioni
    c.execute('CREATE TABLE IF NOT EXISTS team (nome TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS canali (nome TEXT UNIQUE)')
    
    # Popolamento iniziale se vuote
    c.execute("SELECT count(*) FROM team")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO team VALUES (?)", [("Marco",), ("Giulia",)])
    
    c.execute("SELECT count(*) FROM canali")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO canali VALUES (?)", [("Facebook",), ("Instagram",), ("WhatsApp",)])
        
    conn.commit()
    conn.close()

def load_data(table):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def run_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

# Inizializza il DB all'avvio
init_db()

# --- CARICAMENTO STATO SESSIONE ---
if 'refresh' not in st.session_state:
    st.session_state.refresh = False

df_task = load_data("tasks")
team_list = load_data("team")["nome"].tolist()
canali_list = load_data("canali")["nome"].tolist()

# --- FUNZIONI LOGICA ---
def genera_piano():
    testo = st.session_state.input_testo
    inizio = st.session_state.input_data_inizio
    fine = st.session_state.input_data_fine
    frequenza = st.session_state.input_frequenza
    assegnati = ", ".join(st.session_state.input_assegnati)
    canali = ", ".join(st.session_state.input_canali) if st.session_state.input_canali else "Generico"
    foto = st.session_state.input_foto
    
    if not testo.strip() or not assegnati:
        st.error("Compila i campi obbligatori!")
        return

    foto_bytes = foto.getvalue() if foto else None
    foto_nome = foto.name if foto else "Nessuna foto"
    
    conn = sqlite3.connect(DB_NAME)
    temp_date = inizio
    while temp_date <= fine:
        conn.execute('''INSERT INTO tasks 
            (Data_Prevista, Canali, Contenuto, Foto_Nome, Foto_Bytes, Assegnato_a, Stato, Completato_da, Data_Fine) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (temp_date.strftime("%Y-%m-%d"), canali, testo, foto_nome, foto_bytes, assegnati, "🔴 Da fare", "-", "-"))
        temp_date += timedelta(days=frequenza)
    conn.commit()
    conn.close()
    st.toast("Piano salvato nel Database!")

# --- INTERFACCIA ---
st.title("🗄️ Social Manager + Database")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🚀 Nuovo Piano")
    st.text_area("Testo del Post *", key="input_testo")
    st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'], key="input_foto")
    st.multiselect("Canali:", canali_list, key="input_canali")
    st.date_input("Inizio", datetime.now(), key="input_data_inizio")
    st.date_input("Fine", datetime.now() + timedelta(days=14), key="input_data_fine")
    st.number_input("Ogni quanti giorni?", min_value=1, value=1, key="input_frequenza")
    st.multiselect("Assegna a:", team_list, key="input_assegnati")
    if st.button("Salva nel DB", type="primary", use_container_width=True):
        genera_piano()
        st.rerun()

# --- MAIN ---
t1, t2 = st.tabs(["📋 Task Attivi", "⚙️ Impostazioni"])

with t1:
    if not df_task.empty:
        # Trasformiamo la data da testo a oggetto data per visualizzarla meglio
        df_task['Data_Prevista'] = pd.to_datetime(df_task['Data_Prevista']).dt.date
        
        df_vis = df_task.copy()
        df_vis.insert(0, "Seleziona", False)
        
        edited = st.data_editor(
            df_vis.drop(columns=["Foto_Bytes"]),
            column_config={"Seleziona": st.column_config.CheckboxColumn("Gestisci")},
            disabled=[c for c in df_vis.columns if c != "Seleziona"],
            hide_index=True, use_container_width=True
        )
        
        selected_ids = edited[edited["Seleziona"] == True]["ID"].tolist()
        
        for sel_id in selected_ids:
            task = df_task[df_task["ID"] == sel_id].iloc[0]
            with st.expander(f"Task #{sel_id} - {task['Data_Prevista']}", expanded=True):
                c1, c2 = st.columns([3, 2])
                with c1:
                    st.write(f"**Canali:** {task['Canali']}")
                    new_txt = st.text_area("Contenuto", task["Contenuto"], key=f"ed_{sel_id}")
                    if new_txt != task["Contenuto"]:
                        run_query("UPDATE tasks SET Contenuto = ? WHERE ID = ?", (new_txt, sel_id))
                
                with c2:
                    if task["Foto_Bytes"]:
                        st.image(task["Foto_Bytes"], use_container_width=True)
                
                if task["Stato"] != "🟢 Completato":
                    col_b1, col_b2 = st.columns(2)
                    chi = col_b1.selectbox("Eseguito da:", team_list, key=f"u_{sel_id}")
                    if col_b2.button("Segna Completato", key=f"b_{sel_id}"):
                        now = datetime.now().strftime("%d/%m %H:%M")
                        run_query("UPDATE tasks SET Stato='🟢 Completato', Completato_da=?, Data_Fine=? WHERE ID=?", (chi, now, sel_id))
                        st.rerun()
                else:
                    st.success(f"Fatto da {task['Completato_da']} il {task['Data_Fine']}")
                
                if st.button("Elimina Task", key=f"del_{sel_id}"):
                    run_query("DELETE FROM tasks WHERE ID = ?", (sel_id,))
                    st.rerun()
    else:
        st.info("Database vuoto.")

with t2:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Team")
        new_m = st.text_input("Nuovo membro:")
        if st.button("Aggiungi"):
            run_query("INSERT OR IGNORE INTO team VALUES (?)", (new_m,))
            st.rerun()
        for t in team_list:
            if st.button(f"Rimuovi {t}"):
                run_query("DELETE FROM team WHERE nome = ?", (t,))
                st.rerun()
                
    with col_b:
        st.subheader("Canali")
        new_c = st.text_input("Nuovo canale:")
        if st.button("Aggiungi ", key="btn_c"):
            run_query("INSERT OR IGNORE INTO canali VALUES (?)", (new_c,))
            st.rerun()
        for c in canali_list:
            if st.button(f"Rimuovi {c}"):
                run_query("DELETE FROM canali WHERE nome = ?", (c,))
                st.rerun()

st.divider()
if st.sidebar.button("⚠️ SVUOTA TUTTI I TASK"):
    run_query("DELETE FROM tasks")
    st.rerun()
