import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Gestore Task Social", layout="wide")

st.title("📅 Programmatore Task & Post")

# --- SIDEBAR PER NUOVO TASK ---
st.sidebar.header("Crea Nuovo Task")
testo_post = st.sidebar.text_area("Testo del Post")
foto = st.sidebar.file_uploader("Carica Foto", type=['png', 'jpg', 'jpeg'])
data_inizio = st.sidebar.date_input("Data inizio pubblicazione", datetime.now())
data_fine = st.sidebar.date_input("Data fine pubblicazione", datetime.now() + timedelta(days=60))
frequenza = st.sidebar.number_input("Intervallo (giorni)", min_value=1, value=14)
assegnato_a = st.sidebar.selectbox("Assegna a:", ["Persona A", "Persona B", "Persona C"])

if st.sidebar.button("Genera Piano Editoriale"):
    # Logica per calcolare le date distribuite
    date_pubblicazione = []
    current_date = data_inizio
    while current_date <= data_fine:
        date_pubblicazione.append(current_date)
        current_date += timedelta(days=frequenza)
    
    st.success(f"Generati {len(date_pubblicazione)} task!")
    # Qui aggiungeremmo il salvataggio in un database (es. SQLite o Google Sheets)

# --- AREA PRINCIPALE: VISUALIZZAZIONE ---
st.header("📋 Task Programmati")

# Esempio di come apparirebbe la tabella dei task
data = {
    "Data Prevista": [datetime.now().date(), (datetime.now() + timedelta(days=14)).date()],
    "Contenuto": ["Primo post di maggio", "Secondo post di maggio"],
    "Assegnato a": ["Marco", "Giulia"],
    "Stato": ["🔴 Da fare", "🔴 Da fare"],
    "Completato da": ["-", "-"],
    "Data Completamento": ["-", "-"]
}

df = pd.DataFrame(data)

# Tabella interattiva per vedere e modificare i task
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

if st.button("Salva Modifiche"):
    st.info("Modifiche salvate con successo (Simulazione)")
