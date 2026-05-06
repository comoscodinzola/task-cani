import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Social Task Manager", layout="wide")

# --- INIZIALIZZAZIONE DATABASE ---
COLONNE = ["ID", "Data Prevista", "Canali", "Contenuto", "Foto_Nome", "Foto_Bytes", "Assegnato a", "Stato", "Completato da", "Data Fine"]

if 'db_task' not in st.session_state:
    st.session_state.db_task = pd.DataFrame(columns=COLONNE)

# --- FUNZIONE DI GENERAZIONE E RESET ---
def genera_e_reset():
    # Recuperiamo i dati dai widget tramite session_state
    testo = st.session_state.input_testo
    canali = st.session_state.input_canali
    foto = st.session_state.input_foto
    assegnati = st.session_state.input_assegnati
    
    if not testo or not canali:
        st.error("Inserisci almeno il testo e un canale!")
        return

    nuovi_task = []
    current_date = st.session_state.input_data_inizio
    data_fine = st.session_state.input_data_fine
    frequenza = st.session_state.input_frequenza
    
    foto_bytes = foto.getvalue() if foto else None
    foto_nome = foto.name if foto else "Nessuna foto"
    canali_str = ", ".join(canali)
    persone_str = ", ".join(assegnati)
    
    start_id = st.session_state.db_task["ID"].max() + 1 if not st.session_state.db_task.empty else 1
    
    temp_date = current_date
    while temp_date <= data_fine:
        nuovi_task.append({
            "ID": int(start_id),
            "Data Prevista": temp_date,
            "Canali": canali_str,
            "Contenuto": testo,
            "Foto_Nome": foto_nome,
            "Foto_Bytes": foto_bytes,
            "Assegnato a": persone_str,
            "Stato": "🔴 Da fare",
            "Completato da": "-",
            "Data Fine": "-"
        })
        temp_date += timedelta(days=frequenza)
        start_id += 1
    
    # Aggiunta al Database
    st.session_state.db_task = pd.concat([st.session_state.db_task, pd.DataFrame(nuovi_task)], ignore_index=True)
    
    # RESET dei campi: ora Streamlit lo accetta perché siamo dentro un callback
    st.session_state.input_testo = ""
    st.session_state.input_canali = []
    st.session_state.input_assegnati = []
    st.toast("Piano generato con successo!")

st.title("📅 Programmatore Task & Post")

# --- SIDEBAR: CREAZIONE ---
st.sidebar.header("🚀 Crea Nuovo Piano")

st.sidebar.text_area("Testo del Post", key="input_testo")
st.sidebar.file_uploader("Carica Foto", type=['png', 'jpg', 'jpeg'], key="input_foto")

canali_opzioni = ["Facebook", "Instagram", "Stato WhatsApp", "Gruppi WhatsApp", "Community WhatsApp"]
st.sidebar.multiselect("Canali di pubblicazione:", canali_opzioni, key="input_canali")

st.sidebar.date_input("Inizio", datetime.now(), key="input_data_inizio")
st.sidebar.date_input("Fine", datetime.now() + timedelta(days=30), key="input_data_fine")
st.sidebar.number_input("Ogni quanti giorni?", min_value=1, value=7, key="input_frequenza")

nomi_team = ["Persona A", "Persona B", "Persona C", "Marco", "Giulia"]
st.sidebar.multiselect("Assegna a:", nomi_team, key="input_assegnati")

# Usiamo on_click per chiamare la funzione che genera e resetta
st.sidebar.button("Genera Piano Editoriale", on_click=genera_e_reset)

# --- AREA PRINCIPALE ---
st.header("📋 Elenco Task")
if not st.session_state.db_task.empty:
    opzioni_id = st.session_state.db_task["ID"].unique().tolist()
    selected_indices = st.multiselect("🔍 Seleziona ID per gestire il task:", opzioni_id)
    
    st.dataframe(st.session_state.db_task.drop(columns=["Foto_Bytes"]), use_container_width=True)

    if selected_indices:
        for sel_id in selected_indices:
            row = st.session_state.db_task[st.session_state.db_task["ID"] == sel_id]
            if not row.empty:
                idx = row.index[0]
                task = row.iloc[0]
                
                with st.expander(label=f"📦 GESTISCI TASK #{sel_id} - Scadenza: {task['Data Prevista']}", expanded=True):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.info(f"**Canali:** {task['Canali']}")
                        st.text_area("Testo Post (Copia da qui):", task["Contenuto"], height=120, key=f"t_{sel_id}")
                    with c2:
                        if task["Foto_Bytes"]:
                            st.image(task["Foto_Bytes"], caption=task["Foto_Nome"], use_container_width=True)
                            st.download_button("⬇️ Scarica Foto", task["Foto_Bytes"], file_name=task["Foto_Nome"], key=f"d_{sel_id}")
                    
                    if task["Stato"] != "🟢 Completato":
                        persone_list = task["Assegnato a"].split(", ") if task["Assegnato a"] != "" else ["Nessuno"]
                        chi = st.selectbox("Chi lo ha fatto?", persone_list, key=f"who_{sel_id}")
                        if st.button(f"Segna Completato #{sel_id}", key=f"btn_{sel_id}"):
                            st.session_state.db_task.at[idx, "Stato"] = "🟢 Completato"
                            st.session_state.db_task.at[idx, "Completato da"] = chi
                            st.session_state.db_task.at[idx, "Data Fine"] = datetime.now().strftime("%d/%m %H:%M")
                            st.rerun()
                    else:
                        st.success(f"Fatto da {task['Completato da']} il {task['Data Fine']}")
else:
    st.info("Configura il piano a sinistra e clicca su Genera.")

if st.button("🗑️ Svuota Database"):
    st.session_state.db_task = pd.DataFrame(columns=COLONNE)
    st.rerun()
