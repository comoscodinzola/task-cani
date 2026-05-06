import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import base64

st.set_page_config(page_title="Social Task Manager Pro", layout="wide", page_icon="📅")

# --- FUNZIONI DI SUPPORTO ---
def get_image_base64(image_bytes):
    if image_bytes is None:
        return None
    try:
        base64_str = base64.b64encode(image_bytes).decode()
        return f"data:image/png;base64,{base64_str}"
    except:
        return None

# --- FUNZIONI DATABASE ---
DB_NAME = "social_tasks.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                  Titolo TEXT, Data_Prevista TEXT, Canali TEXT, Contenuto TEXT, 
                  Foto_Nome TEXT, Foto_Bytes BLOB, Assegnato_a TEXT, 
                  Stato TEXT, Completato_da TEXT, Data_Fine TEXT)''')
    conn.commit()
    conn.close()

def load_data(table):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY Data_Prevista ASC", conn)
    conn.close()
    return df

def run_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

init_db()
df_task = load_data("tasks")
team_list = pd.read_sql_query("SELECT * FROM team", sqlite3.connect(DB_NAME))["nome"].tolist() if not load_data("team").empty else ["Marco", "Giulia"]
canali_list = pd.read_sql_query("SELECT * FROM canali", sqlite3.connect(DB_NAME))["nome"].tolist() if not load_data("canali").empty else ["Facebook", "Instagram"]

# --- FUNZIONE GENERAZIONE ---
def genera_piano():
    titolo = st.session_state.input_titolo
    testo = st.session_state.input_testo
    inizio = st.session_state.input_data_inizio
    fine = st.session_state.input_data_fine
    frequenza = st.session_state.input_frequenza
    assegnati = ", ".join(st.session_state.input_assegnati)
    canali = ", ".join(st.session_state.input_canali) if st.session_state.input_canali else "Generico"
    foto = st.session_state.input_foto
    
    if not testo.strip() or not assegnati or not titolo.strip():
        st.error("Compila Titolo, Testo e Responsabile!")
        return

    foto_bytes = foto.getvalue() if foto else None
    foto_nome = foto.name if foto else "Nessuna foto"
    
    conn = sqlite3.connect(DB_NAME)
    temp_date = inizio
    while temp_date <= fine:
        conn.execute('''INSERT INTO tasks 
            (Titolo, Data_Prevista, Canali, Contenuto, Foto_Nome, Foto_Bytes, Assegnato_a, Stato, Completato_da, Data_Fine) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (titolo, temp_date.strftime("%Y-%m-%d"), canali, testo, foto_nome, foto_bytes, assegnati, "🔴 Da fare", "-", "-"))
        temp_date += timedelta(days=frequenza)
    conn.commit()
    conn.close()
    st.rerun()

# --- INTERFACCIA ---
st.title("📅 Social Manager Pro")

with st.sidebar:
    st.header("🚀 Crea Piano")
    st.text_input("Titolo *", key="input_titolo")
    st.text_area("Testo *", key="input_testo")
    st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'], key="input_foto")
    st.multiselect("Canali:", canali_list, key="input_canali")
    st.date_input("Inizio", datetime.now(), key="input_data_inizio")
    st.date_input("Fine", datetime.now() + timedelta(days=7), key="input_data_fine")
    st.number_input("Ogni quanti giorni?", min_value=1, value=1, key="input_frequenza")
    st.multiselect("Assegna a:", team_list, key="input_assegnati")
    if st.button("Salva nel Database", type="primary", use_container_width=True):
        genera_piano()

t1, t2 = st.tabs(["📋 Elenco Task", "⚙️ Configurazione"])

with t1:
    if not df_task.empty:
        df_vis = df_task.copy()
        df_vis['Data_Prevista'] = pd.to_datetime(df_vis['Data_Prevista']).dt.strftime('%d-%m-%Y')
        df_vis['Anteprima'] = df_vis['Foto_Bytes'].apply(get_image_base64)
        df_vis.insert(0, "Seleziona", False)
        
        # --- COLONNE AGGIORNATE (Senza ID, con Responsabile) ---
        col_show = ["Seleziona", "Anteprima", "Titolo", "Data_Prevista", "Assegnato_a", "Stato"]
        
        edited = st.data_editor(
            df_vis[col_show],
            column_config={
                "Seleziona": st.column_config.CheckboxColumn("", width="small"), # Stretta e senza etichetta
                "Anteprima": st.column_config.ImageColumn("Foto"),
                "Titolo": st.column_config.TextColumn("Titolo", width="medium"),
                "Assegnato_a": "Responsabile",
                "Data_Prevista": "Scadenza",
            },
            disabled=[c for c in col_show if c != "Seleziona"],
            hide_index=True, 
            use_container_width=True, 
            key="main_editor",
            row_height=70
        )
        
        # Recuperiamo l'ID originale tramite l'indice della riga selezionata
        selected_indices = edited[edited["Seleziona"] == True].index.tolist()
        
        if selected_indices:
            st.divider()
            for idx in selected_indices:
                task = df_task.iloc[idx]
                sel_id = task["ID"]
                
                with st.expander(f"📦 Dettaglio: {task['Titolo']} - {task['Data_Prevista']}", expanded=True):
                    c1, c2 = st.columns([3, 2])
                    with c1:
                        new_txt = st.text_area("Copy:", task["Contenuto"], key=f"txt_{sel_id}", height=150)
                        if new_txt != task["Contenuto"]:
                            run_query("UPDATE tasks SET Contenuto = ? WHERE ID = ?", (new_txt, sel_id))
                        st.caption(f"Social: {task['Canali']} | Responsabile: {task['Assegnato_a']}")
                    
                    with c2:
                        if task["Foto_Bytes"]:
                            st.image(task["Foto_Bytes"], use_container_width=True)
                    
                    st.divider()
                    ca1, ca2, ca3 = st.columns([2, 2, 1])
                    if task["Stato"] != "🟢 Completato":
                        chi = ca1.selectbox("Chi completa?", team_list, key=f"u_{sel_id}")
                        if ca2.button("✅ Segna Fatto", key=f"b_{sel_id}", use_container_width=True):
                            now = datetime.now().strftime("%d-%m-%Y %H:%M")
                            run_query("UPDATE tasks SET Stato='🟢 Completato', Completato_da=?, Data_Fine=? WHERE ID=?", (chi, now, sel_id))
                            st.rerun()
                    else:
                        ca1.success(f"Completato da {task['Completato_da']}")
                    
                    if ca3.button("🗑️ Elimina", key=f"del_{sel_id}", use_container_width=True):
                        run_query("DELETE FROM tasks WHERE ID = ?", (sel_id,))
                        st.rerun()
    else:
        st.info("Nessun task in programma.")

with t2:
    st.info("Qui puoi gestire i membri del team e i canali social (come nelle versioni precedenti).")
