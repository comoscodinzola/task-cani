import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Social Task Manager", layout="wide")

# --- DATABASE IN MEMORIA ---
if 'db_task' not in st.session_state:
    st.session_state.db_task = pd.DataFrame(columns=[
        "ID", "Data Prevista", "Canali", "Contenuto", "Foto_Nome", "Foto_Bytes", "Assegnato a", "Stato", "Completato da", "Data Fine"
    ])

st.title("📅 Programmatore Task & Post")

# --- SIDEBAR: CREAZIONE ---
st.sidebar.header("🚀 Crea Nuovo Piano")
testo_post = st.sidebar.text_area("Testo del Post")
foto = st.sidebar.file_uploader("Carica Foto", type=['png', 'jpg', 'jpeg'])

canali_opzioni = ["Facebook", "Instagram", "Stato WhatsApp", "Gruppi WhatsApp", "Community WhatsApp"]
canali_scelti = st.sidebar.multiselect("Canali di pubblicazione:", canali_opzioni)

data_inizio = st.sidebar.date_input("Inizio", datetime.now())
data_fine = st.sidebar.date_input("Fine", datetime.now() + timedelta(days=30))
frequenza = st.sidebar.number_input("Ogni quanti giorni?", min_value=1, value=7)

nomi_team = ["Persona A", "Persona B", "Persona C", "Marco", "Giulia"]
assegnati = st.sidebar.multiselect("Assegna a:", nomi_team)

if st.sidebar.button("Genera Piano Editoriale"):
    nuovi_task = []
    current_date = data_inizio
    foto_bytes = foto.getvalue() if foto else None
    foto_nome = foto.name if foto else "Nessuna foto"
    canali_str = ", ".join(canali_scelti)
    persone_str = ", ".join(assegnati)
    
    while current_date <= data_fine:
        task_id = len(st.session_state.db_task) + len(nuovi_task) + 1
        nuovi_task.append({
            "ID": task_id,
            "Data Prevista": current_date,
            "Canali": canali_str,
            "Contenuto": testo_post,
            "Foto_Nome": foto_nome,
            "Foto_Bytes": foto_bytes,
            "Assegnato a": persone_str,
            "Stato": "🔴 Da fare",
            "Completato da": "-",
            "Data Fine": "-"
        })
        current_date += timedelta(days=frequenza)
    
    st.session_state.db_task = pd.concat([st.session_state.db_task, pd.DataFrame(nuovi_task)], ignore_index=True)
    st.success("Piano generato!")

# --- AREA PRINCIPALE: TABELLA ---
st.header("📋 Elenco Task")
if not st.session_state.db_task.empty:
    # Selezione del task da gestire
    selected_indices = st.multiselect("Seleziona i task da visualizzare o gestire (ID):", st.session_state.db_task["ID"].tolist())
    
    # Mostriamo la tabella completa (sola lettura per ordine)
    st.dataframe(st.session_state.db_task.drop(columns=["Foto_Bytes"]), use_container_width=True)

    # --- DETTAGLIO TASK SELEZIONATO ---
    if selected_indices:
        st.divider()
        st.header("🔍 Gestione Task Selezionato")
        
        for sel_id in selected_indices:
            idx = st.session_state.db_task[st.session_state.db_task["ID"] == sel_id].index[0]
            task = st.session_state.db_task.iloc[idx]
            
            with st.expander(label=f"TASK #{sel_id} - Scadenza: {task['Data Prevista']}", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**📢 Canali:** {task['Canali']}")
                    st.write(f"**👥 Assegnati:** {task['Assegnato a']}")
                    st.text_area("Testo da copiare:", task["Contenuto"], height=100, key=f"txt_{sel_id}")
                
                with col2:
                    if task["Foto_Bytes"]:
                        st.image(task["Foto_Bytes"], width=150)
                        st.download_button(label="⬇️ Scarica Foto", data=task["Foto_Bytes"], file_name=task["Foto_Nome"], key=f"dl_{sel_id}")
                    else:
                        st.warning("Nessuna foto")

                # Azione di completamento
                if task["Stato"] != "🟢 Completato":
                    st.subheader("✅ Segna come completato")
                    chi = st.selectbox("Chi sta completando il task?", task["Assegnato a"].split(", "), key=f"chi_{sel_id}")
                    if st.button(f"Conferma Task #{sel_id}", key=f"btn_{sel_id}"):
                        st.session_state.db_task.at[idx, "Stato"] = "🟢 Completato"
                        st.session_state.db_task.at[idx, "Completato da"] = chi
                        st.session_state.db_task.at[idx, "Data Fine"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                        st.rerun()
                else:
                    st.success(f"Completato da {task['Completato da']} il {task['Data Fine']}")

else:
    st.info("Crea un piano dalla sidebar per vedere i task.")

if st.button("Svuota tutto"):
    st.session_state.db_task = pd.DataFrame(columns=["ID", "Data Prevista", "Canali", "Contenuto", "Foto_Nome", "Foto_Bytes", "Assegnato a", "Stato", "Completato da", "Data Fine"])
    st.rerun()
