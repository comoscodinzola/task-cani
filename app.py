# ... (resto del codice invariato fino alla visualizzazione dell'expander)

        if selected_indices:
            st.divider()
            for idx in selected_indices:
                task = df_task.iloc[idx]
                tid = task["ID"]
                with st.expander(f"📦 Dettaglio: {task['Titolo']} - {task['Data_Prevista']}", expanded=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        # --- NUOVO: MOSTRA E MODIFICA IL LINK NEL DETTAGLIO ---
                        current_link = task["Link"] if task["Link"] else ""
                        new_link = st.text_input("🔗 Link Risorsa (URL):", current_link, key=f"link_edit_{tid}")
                        
                        # Se il link esiste, mostriamo anche un piccolo pulsante cliccabile per comodità
                        if new_link:
                            st.markdown(f"[➡️ Clicca qui per aprire il link]({new_link})")
                        
                        st.write("---")
                        
                        # Modifica del testo del post
                        new_txt = st.text_area("📝 Testo del post:", task["Contenuto"], key=f"t_{tid}", height=150)
                        
                        if st.button("💾 Salva Modifiche", key=f"s_{tid}", type="primary"):
                            run_query("UPDATE tasks SET Contenuto = ?, Link = ? WHERE ID = ?", (new_txt, new_link, tid))
                            st.toast("Modifiche salvate con successo!")
                            st.rerun()
                            
                    with c2:
                        if task["Foto_Bytes"]: 
                            st.image(task["Foto_Bytes"], caption="Immagine allegata")
                    
                    st.divider()
                    # Azioni di stato (Completato / Elimina)
                    # ... (resto del codice per le azioni)
