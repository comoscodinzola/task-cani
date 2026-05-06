import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import base64  # Necessario per convertire l'immagine

st.set_page_config(page_title="Social Task Manager Pro", layout="wide", page_icon="📅")

# --- FUNZIONI DI SUPPORTO ---
def get_image_base64(image_bytes):
    """Converte i bytes dell'immagine in una stringa base64 leggibile dall'editor"""
    if image_bytes is None:
        return None
    try:
        base64_str = base64.b64encode(image_bytes).decode()
        return f"data:image/png;base64,{base64_str}"
    except:
        return None

# --- FUNZIONI DATABASE SQLITE ---
DB_NAME = "social_tasks.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                  Titolo TEXT, Data_Prevista TEXT, Canali TEXT, Contenuto TEXT, 
                  Foto_Nome TEXT, Foto_Bytes BLOB, Assegnato_a TEXT, 
                  Stato TEXT, Completato_da TEXT, Data_Fine TEXT)''')
    
    # Migrazione colonna Titolo se mancante
    c.execute("PRAGMA table_info(tasks)")
    columns = [column[1] for column in c.fetchall()]
    if 'Titolo' not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN Titolo TEXT DEFAULT 'Senza Titolo'")
        
    c.execute('CREATE TABLE IF NOT EXISTS team (nome TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS canali (nome TEXT UNIQUE)')
    
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
    if table == "tasks":
        df = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY Data_Prevista ASC, ID ASC", conn)
    else:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def run_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

init_db()

# --- CARICAMENTO DATI ---
df_task = load_data("tasks")
team_list = load_data("team")["nome"].tolist()
canali_list = load_data("canali")["nome"].tolist()

# --- FUNZIONI LOGICA ---
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
        st.error("Compila tutti i campi obbligatori!")
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
    st.toast("Piano salvato!")

# --- INTERFACCIA ---
st.title("📅 Social Manager Pro")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🚀 Crea Piano")
    st.text_input("Titolo *", key="input_titolo")
    st.text_area("Testo *", key="input_testo")
    st.file_uploader("Immagine", type=['png', 'jpg', 'jpeg'], key="input_foto")
    st.multiselect("Canali:", canali_list, key="input_canali")
    st.date_input("Inizio", datetime.now(), key="input_data_inizio", format="DD/MM/YYYY")
    st.date_input("Fine", datetime.now() + timedelta(days=14), key="input_data_fine", format="DD/MM/YYYY")
    st.number_input("Ogni quanti giorni?", min_value=1, value=1, key="input_frequenza")
    st.multiselect("Assegna a:", team_list, key="input_assegnati")
    if st.button("Salva nel Database", type="primary", use_container_width=True):
        genera_piano()
        st.rerun()

# --- AREA PRINCIPALE ---
t1, t2 = st.tabs(["📋 Elenco Task", "⚙️ Impostazioni"])

with t1:
    if not df_task.empty:
        df_vis = df_task.copy()
        df_vis['Data_Prevista'] = pd.to_datetime(df_vis['Data_Prevista']).dt.strftime('%d-%m-%Y')
        
        # --- FIX: CONVERSIONE IMMAGINE PER ANTEPRIMA ---
        df_vis['Anteprima'] = df_vis['Foto_Bytes'].apply(get_image_base64)
        
        df_vis.insert(0, "Seleziona", False)
        
        # Seleziona colonne
        col_show = ["Seleziona", "Anteprima", "Titolo", "Data_Prevista", "Stato", "ID"]
        
        edited = st.data_editor(
            df_vis[col_show],
            column_config={
                "Seleziona": st.column_config.CheckboxColumn("Gestisci"),
                "Anteprima": st.column_config.ImageColumn("Anteprima"),
                "ID": st.column_config.NumberColumn("ID", format="%d")
            },
            disabled=[c for c in col_show if c != "Seleziona"],
            hide_index=True, 
            use_container_width=True, 
            key="main_editor",
            row_height=70 # Aumentato per visibilità
        )
        
        selected_ids = edited[edited["Seleziona"] == True]["ID"].tolist()
        
        if selected_ids:
            st.divider()
            for sel_id in selected_ids:
                task = df_task[df_task["ID"] == sel_id].iloc[0]
                data_f = datetime.strptime(task['Data_Prevista'], "%Y-%m-%d").strftime("%d-%m-%Y")
                
                with st.expander(f"📦 {task['Titolo']} (#{sel_id}) - {data_f}", expanded=True):
                    c1, c2 = st.columns([3, 2])
                    with c1:
                        new_tit = st.text_input("Modifica Titolo:", task["Titolo"], key=f"t_{sel_id}")
                        if new_tit != task["Titolo"]:
                            run_query("UPDATE tasks SET Titolo = ? WHERE ID = ?", (new_tit, sel_id))
                        
                        st.info(f"**Social:** {task['Canali']} | **Chi:** {task['Assegnato_a']}")
                        new_txt = st.text_area("Copy:", task["Contenuto"], key=f"txt_{sel_id}", height=120)
                        if new_txt != task["Contenuto"]:
                            run_query("UPDATE tasks SET Contenuto = ? WHERE ID = ?", (new_txt, sel_id))
                    
                    with c2:
                        if task["Foto_Bytes"]:
                            st.image(task["Foto_Bytes"], use_container_width=True)
                            st.download_button("💾 Scarica", task["Foto_Bytes"], file_name=task["Foto_Nome"], key=f"dl_{sel_id}")
                    
                    st.divider()
                    col_a1, col_a2, col_a3 = st.columns([2, 2, 1])
                    if task["Stato"] != "🟢 Completato":
                        chi = col_a1.selectbox("Eseguito da:", team_list, key=f"user_{sel_id}")
                        if col_a2.button("✅ Completa", key=f"btn_{sel_id}", use_container_width=True):
                            now = datetime.now().strftime("%d-%m-%Y %H:%M")
                            run_query("UPDATE tasks SET Stato='🟢 Completato', Completato_da=?, Data_Fine=? WHERE ID=?", (chi, now, sel_id))
                            st.rerun()
                    else:
                        col_a1.success(f"Fatto da {task['Completato_da']}")
                    
                    if col_a3.button("🗑️ Elimina", key=f"del_{sel_id}", use_container_width=True):
                        run_query("DELETE FROM tasks WHERE ID = ?", (sel_id,))
                        st.rerun()
    else:
        st.info("Nessun task presente.")

with t2:
    # Codice Team/Canali (Invariato)
    c_a, c_b = st.columns(2)
    with c_a:
        st.subheader("👥 Team")
        new_m = st.text_input("Aggiungi membro:")
        if st.button("Aggiungi"):
            run_query("INSERT OR IGNORE INTO team VALUES (?)", (new_m,))
            st.rerun()
        for t in team_list:
            cols = st.columns([4, 1])
            cols[0].write(t)
            if cols[1].button("X", key=f"rm_t_{t}"):
                run_query("DELETE FROM team WHERE nome = ?", (t,))
                st.rerun()
    with c_b:
        st.subheader("📢 Canali")
        new_c = st.text_input("Aggiungi social:")
        if st.button("Aggiungi Social"):
            run_query("INSERT OR IGNORE INTO canali VALUES (?)", (new_c,))
            st.rerun()
        for c in canali_list:
            cols = st.columns([4, 1])
            cols[0].write(c)
            if cols[1].button("X", key=f"rm_c_{c}"):
                run_query("DELETE FROM canali WHERE nome = ?", (c,))
                st.rerun()

if st.sidebar.button("🚨 CANCELLA TUTTI I TASK"):
    run_query("DELETE FROM tasks")
    st.rerun()
