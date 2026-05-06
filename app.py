import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Social Task Manager", layout="wide")

# --- INIZIALIZZAZIONE DATABASE ---
COLONNE = ["ID", "Data Prevista", "Canali", "Contenuto", "Foto_Nome", "Foto_Bytes", "Assegnato a", "Stato", "Completato da", "Data Fine"]

if 'db_task' not in st.session_state:
    st.session_state.db_task = pd.DataFrame(columns=COLONNE)

if 'team' not in st.session_state:
    st.session_state.team = ["Marco", "Giulia"]

if 'canali_opzioni' not in st.session_state:
    st.session_state.canali_opzioni = ["Facebook", "Instagram", "Stato WhatsApp"]

# --- FUNZIONI DI SERVIZIO ---
def genera_e_reset():
    testo = st.session_state.input_testo
    inizio = st.session_state.input_data_inizio
    fine = st.session_state.input_data_fine
    frequenza = st.session_state.input_frequenza
    assegnati = st.session_state.input_assegnati
    
    # Validazione
    if not testo.strip() or not assegnati or inizio > fine:
        st.error("⚠️ Compila tutti i campi obbligatori correttamente!")
        return

    nuovi_task = []
    foto = st.session_state.input_foto
    foto_bytes = foto.getvalue() if foto else None
    foto_nome = foto.name if foto else "Nessuna foto"
    canali_str = ", ".join(st.session_state.input_canali) if st.session_state.input_canali else "Nessun canale"
    
    start_id = st.session_state.db_task["ID"].max() + 1 if not st.session_state.db_task.empty else 1
    
    temp_date = inizio
    while temp_date <= fine:
        nuovi_task.append({
            "ID": int(start_id),
            "Data Prevista": temp_date,
            "Canali": canali_str,
            "Contenuto": testo,
            "Foto_Nome": foto_nome,
            "Foto_Bytes": foto_bytes,
            "Assegnato a": ", ".join(assegnati),
            "Stato": "🔴 Da fare",
            "Completato da": "-",
            "Data Fine": "-"
        })
        temp_date += timedelta(days=frequenza)
        start_id += 1
    
    st.session_state.db_task = pd.concat([st.session_state.db_task, pd.DataFrame(nuovi_task)], ignore_index=True)
    st.session_state.input_testo = ""
    st.session_state.input_canali = []
    st.session_state.input_assegnati = []
    st.toast("Piano generato!")

st.title("📅 Programmatore Task & Post")

# --- SIDEBAR ---
st.sidebar.header("🚀 Crea Nuovo Piano")
st.sidebar.text_area("Testo del Post *", key="input_testo")
st.sidebar.file_uploader("Carica Foto", type=['png', 'jpg', 'jpeg'], key="input_foto")
st.sidebar.multiselect("Canali (Opzionale):", st.session_state.canali_opzioni, key="input_canali")
st.sidebar.date_input("Inizio *", datetime.now(), key="input_data_inizio")
st.sidebar.date_input("Fine *", datetime.now() + timedelta(days=30), key="input_data_fine")
st.sidebar.number_input("Ogni quanti giorni? *", min_value=1, value=7, key="input_frequenza")
st.sidebar.multiselect("Assegna a: *", st.session_state.team, key="input_assegnati")
st.sidebar.button("Genera Piano Editoriale", on_click=genera_e_reset)

# --- AREA PRINCIPALE ---
tab1, tab2 = st.tabs(["📋 Elenco Task", "⚙️ Gestione Impostazioni"])

with tab1:
    if not st.session_state.db_task.empty:
        st.subheader("Seleziona i task per gestirli")
        
        # 1. Prepariamo il dataframe per la visualizzazione
        df_display = st.session_state.db_task.copy()
        # Aggiungiamo una colonna "Seleziona" all'inizio
        df_display.insert(0, "Seleziona", False)
        
        # 2. Visualizzazione con DATA EDITOR (permette le checkbox)
        edited_df = st.data_editor(
            df_display.drop(columns=["Foto_Bytes"]),
            column_config={
                "Seleziona": st.column_config.CheckboxColumn(
                    "Seleziona",
                    help="Spunta per gestire questo task",
                    default=False,
                )
            },
            disabled=[c for c in df_display.columns if c != "Seleziona"], # Solo la colonna Seleziona è cliccabile
            hide_index=True,
            use_container_width=True,
            key="task_editor"
        )

        # 3. Identifichiamo quali ID sono stati selezionati
        selected_ids = edited_df[edited_df["Seleziona"] == True]["ID"].tolist()

        if selected_ids:
            st.divider()
            for sel_id in selected_ids:
                row = st.session_state.db_task[st.session_state.db_task["ID"] == sel_id]
                if not row.empty:
                    idx = row.index[0]
                    task = row.iloc[0]
                    
                    with st.expander(label=f"📦 GESTISCI TASK #{sel_id} - Scadenza: {task['Data Prevista']}", expanded=True):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.info(f"**Canali:** {task['Canali']}")
                            st.text_area("Contenuto:", task["Contenuto"], height=100, key=f"t_{sel_id}")
                        with c2:
                            if task["Foto_Bytes"]:
                                st.image(task["Foto_Bytes"], use_container_width=True)
                                st.download_button("⬇️ Foto", task["Foto_Bytes"], file_name=task["Foto_Nome"], key=f"d_{sel_id}")
                        
                        if task["Stato"] != "🟢 Completato":
                            chi = st.selectbox("Chi lo ha fatto?", st.session_state.team, key=f"who_{sel_id}")
                            if st.button(f"Segna Completato #{sel_id}", key=f"btn_{sel_id}"):
                                st.session_state.db_task.at[idx, "Stato"] = "🟢 Completato"
                                st.session_state.db_task.at[idx, "Completato da"] = chi
                                st.session_state.db_task.at[idx, "Data Fine"] = datetime.now().strftime("%d/%m %H:%M")
                                st.rerun()
                        else:
                            st.success(f"Completato da {task['Completato da']}")
    else:
        st.info("Nessun task presente. Genera un piano dalla sidebar.")

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.header("👥 Team")
        n_m = st.text_input("Nome:", key="nm")
        if st.button("Aggiungi"):
            if n_m and n_m not in st.session_state.team:
                st.session_state.team.append(n_m); st.rerun()
        for m in st.session_state.team:
            c_a, c_b = st.columns([3, 1])
            c_a.write(m)
            if c_b.button("X", key=f"dm_{m}"):
                st.session_state.team.remove(m); st.rerun()
    with col2:
        st.header("📢 Canali")
        n_c = st.text_input("Canale:", key="nc")
        if st.button("Aggiungi ", key="ac"):
            if n_c and n_c not in st.session_state.canali_opzioni:
                st.session_state.canali_opzioni.append(n_c); st.rerun()
        for c in st.session_state.canali_opzioni:
            c_a, c_b = st.columns([3, 1])
            c_a.write(c)
            if c_b.button("X", key=f"dc_{c}"):
                st.session_state.canali_opzioni.remove(c); st.rerun()

st.divider()
if st.button("🗑️ Svuota Tutto"):
    st.session_state.db_task = pd.DataFrame(columns=COLONNE); st.rerun()
