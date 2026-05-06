import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Gestore Task Social", layout="wide")

st.title("📅 Programmatore Task & Post")

# Inizializziamo il database in memoria se non esiste ancora
if 'db_task' not in st.session_state:
    st.session_state.db_task = pd.DataFrame(columns=[
        "Data Prevista", "Contenuto", "Foto", "Assegnato a", "Stato", "Completato da", "Data Fine"
    ])

# --- SIDEBAR PER NUOVO TASK ---
st.sidebar.header("Crea Nuovo Task")
testo_post = st.sidebar.text_area("Testo del Post")
foto = st.sidebar.file_uploader("Carica Foto", type=['png', 'jpg', 'jpeg'])
data_inizio = st.sidebar.date_input("Data inizio pubblicazione", datetime.now())
data_fine = st.sidebar.date_input("Data fine pubblicazione", datetime.now() + timedelta(days=60))
frequenza = st.sidebar.number_input("Intervallo (giorni)", min_value=1, value=7)

# MODIFICA: Ora puoi scegliere più persone
nomi_team = ["Persona A", "Persona B", "Persona C", "Marco", "Giulia"]
assegnati = st.sidebar.multiselect("Assegna a:", nomi_team)

if st.sidebar.button("Genera Piano Editoriale"):
    nuovi_task = []
    current_date = data_inizio
    nome_foto = foto.name if foto else "Nessuna foto"
    
    # Trasformiamo la lista di persone in una stringa leggibile
    persone_str = ", ".join(assegnati) if assegnati else "Non assegnato"

    while current_date <= data_fine:
        nuovi_task.append({
            "Data Prevista": current_date,
            "Contenuto": testo_post,
            "Foto": nome_foto,
            "Assegnato a": persone_str,
            "Stato": "🔴 Da fare",
            "Completato da": "-",
            "Data Fine": "-"
        })
        current_date += timedelta(days=frequenza)
    
    # Aggiungiamo i nuovi task a quelli esistenti
    df_nuovi = pd.DataFrame(nuovi_task)
    st.session_state.db_task = pd.concat([st.session_state.db_task, df_nuovi], ignore_index=True)
    st.success(f"Generati {len(nuovi_task)} task con successo!")

# --- AREA PRINCIPALE: VISUALIZZAZIONE ---
st.header("📋 Task Programmati")

if not st.session_state.db_task.empty:
    # Rendiamo la tabella modificabile
    # Puoi cambiare lo Stato o scrivere chi lo ha fatto direttamente nella tabella
    st.session_state.db_task = st.data_editor(
        st.session_state.db_task, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Stato": st.column_config.SelectboxColumn(
                options=["🔴 Da fare", "🟡 In corso", "🟢 Completato"]
            )
        }
    )
else:
    st.info("Nessun task generato. Usa il menu a sinistra per iniziare.")

if st.button("Pulisci tutto"):
    st.session_state.db_task = pd.DataFrame(columns=["Data Prevista", "Contenuto", "Foto", "Assegnato a", "Stato", "Completato da", "Data Fine"])
    st.rerun()
