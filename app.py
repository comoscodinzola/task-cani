import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Social Task Manager Pro", layout="wide", page_icon="📅")

# --- COSTANTI E CSS ---
COLONNE = ["ID", "Data Prevista", "Canali", "Contenuto", "Foto_Nome", "Foto_Bytes", "Assegnato a", "Stato", "Completato da", "Data Fine"]

# --- INIZIALIZZAZIONE DATABASE ---
if 'db_task' not in st.session_state:
    st.session_state.db_task = pd.DataFrame(columns=COLONNE)

if 'team' not in st.session_state:
    st.session_state.team = ["Marco", "Giulia"]

if 'canali_opzioni' not in st.session_state:
    st.session_state.canali_opzioni = ["Facebook", "Instagram", "Stato WhatsApp"]

# --- FUNZIONI DI SERVIZIO ---
def genera_e_reset():
    # Recupero dati dallo stato
    testo = st.session_state.input_testo
    inizio = st.session_state.input_data_inizio
    fine = st.session_state.input_data_fine
    frequenza = st.session_state.input_frequenza
    assegnati = st.session_state.input_assegnati
    canali = st.session_state.input_canali
    foto = st.session_state.input_foto
    
    # Validazione rapida
    if not testo.strip() or not assegnati:
        st.error("⚠️ Inserisci almeno il testo e un assegnatario!")
        return

    nuovi_task = []
    foto_bytes = foto.getvalue() if foto else None
    foto_nome = foto.name if foto else "Nessuna foto"
    canali_str = ", ".join(canali) if canali else "Generico"
    
    # Calcolo ID di partenza
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
    
    # Aggiornamento DataFrame
    nuovi_df = pd.DataFrame(nuovi_task)
    st.session_state.db_task = pd.concat([st.session_state.db_task, nuovi_df], ignore_index=True)
    
    # Reset manuale campi
    st.toast(f"✅ Generati {len(nuovi_task)} task con successo!")

# --- INTERFACCIA ---
st.title("📅 Social Task Manager")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🚀 Nuovo Piano")
    st.text_area("Cosa pubblicare? *", key="input_testo", placeholder="Scrivi qui il copy del post...")
    st.file_uploader("Allega immagine", type=['png', 'jpg', 'jpeg'], key="input_foto")
    st.multiselect("Social Media:", st.session_state.canali_opzioni, key="input_canali")
    
    c_data1, c_data2 = st.columns(2)
    c_data1.date_input("Dal", datetime.now(), key="input_data_inizio")
    c_data2.date_input("Al", datetime.now() + timedelta(days=14), key="input_data_fine")
    
    st.number_input("Ripeti ogni (giorni):", min_value=1, value=1, key="input_frequenza")
    st.multiselect("Assegna a team:", st.session_state.team, key="input_assegnati")
    
    st.button("📅 Genera Programmazione", on_click=genera_e_reset, use_container_width=True, type="primary")

# --- AREA PRINCIPALE ---
tab1, tab2 = st.tabs(["📋 Calendario Task", "⚙️ Team & Social"])

with tab1:
    if not st.session_state.db_task.empty:
        # Filtri veloci
        st.write("### Lista Attività")
        
        # Prepariamo il DF per l'editor
        df_visibile = st.session_state.db_task.copy()
        df_visibile.insert(0, "Seleziona", False)
        
        # Mostriamo solo colonne utili
        colonne_da_mostrare = ["Seleziona", "ID", "Data Prevista", "Stato", "Canali", "Assegnato a", "Completato da"]
        
        edited_df = st.data_editor(
            df_visibile[colonne_da_mostrare],
            column_config={
                "Seleziona": st.column_config.CheckboxColumn("Gestisci", default=False),
                "Data Prevista": st.column_config.DateColumn("Data"),
                "Stato": st.column_config.TextColumn("Stato", disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            key="editor_principale"
        )

        selected_ids = edited_df[edited_df["Seleziona"] == True]["ID"].tolist()

        if selected_ids:
            st.markdown("---")
            for sel_id in selected_ids:
                row = st.session_state.db_task[st.session_state.db_task["ID"] == sel_id]
                if not row.empty:
                    idx = row.index[0]
                    task = row.iloc[0]
                    
                    with st.expander(label=f"📝 Gestione Task #{sel_id} - {task['Data Prevista']}", expanded=True):
                        c1, c2 = st.columns([3, 2])
                        with c1:
                            st.markdown(f"**📢 Canali:** {task['Canali']}")
                            st.markdown(f"**👤 Assegnato a:** {task['Assegnato a']}")
                            new_content = st.text_area("Modifica Testo:", task["Contenuto"], key=f"edit_t_{sel_id}")
                            # Aggiornamento testo real-time
                            st.session_state.db_task.at[idx, "Contenuto"] = new_content
                        
                        with c2:
                            if task["Foto_Bytes"]:
                                st.image(task["Foto_Bytes"], caption=task["Foto_Nome"], use_container_width=True)
                                st.download_button("💾 Scarica Foto", task["Foto_Bytes"], file_name=task["Foto_Nome"], key=f"dl_{sel_id}")
                            else:
                                st.warning("Nessuna immagine allegata")
                        
                        if task["Stato"] != "🟢 Completato":
                            col_done1, col_done2 = st.columns([2,1])
                            chi = col_done1.selectbox("Chi ha completato?", st.session_state.team, key=f"user_{sel_id}")
                            if col_done2.button("✅ Segna come fatto", key=f"done_{sel_id}", use_container_width=True):
                                st.session_state.db_task.at[idx, "Stato"] = "🟢 Completato"
                                st.session_state.db_task.at[idx, "Completato da"] = chi
                                st.session_state.db_task.at[idx, "Data Fine"] = datetime.now().strftime("%d/%m %H:%M")
                                st.rerun()
                        else:
                            st.success(f"✅ Completato da {task['Completato da']} il {task['Data Fine']}")
    else:
        st.info("💡 La lista è vuota. Usa la barra laterale per creare il tuo primo piano editoriale!")

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👥 Gestione Team")
        nuovo_membro = st.text_input("Aggiungi collaboratore:")
        if st.button("Aggiungi Membro"):
            if nuovo_membro and nuovo_membro not in st.session_state.team:
                st.session_state.team.append(nuovo_membro)
                st.rerun()
        
        for m in st.session_state.team:
            c_a, c_b = st.columns([4, 1])
            c_a.write(f"- {m}")
            if c_b.button("🗑️", key=f"del_m_{m}"):
                st.session_state.team.remove(m)
                st.rerun()

    with col2:
        st.subheader("📢 Canali Social")
        nuovo_canale = st.text_input("Aggiungi social/canale:")
        if st.button("Aggiungi Canale"):
            if nuovo_canale and nuovo_canale not in st.session_state.canali_opzioni:
                st.session_state.canali_opzioni.append(nuovo_canale)
                st.rerun()
        
        for c in st.session_state.canali_opzioni:
            c_a, c_b = st.columns([4, 1])
            c_a.write(f"- {c}")
            if c_b.button("🗑️", key=f"del_c_{c}"):
                st.session_state.canali_opzioni.remove(c)
                st.rerun()

# --- FOOTER ---
st.divider()
c_foot1, c_foot2, c_foot3 = st.columns([1,1,1])
if c_foot2.button("🚨 Svuota Intero Database", use_container_width=True):
    st.session_state.db_task = pd.DataFrame(columns=COLONNE)
    st.rerun()
