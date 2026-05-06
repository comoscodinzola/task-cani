def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 1. Crea la tabella se non esiste
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                  Titolo TEXT, Data_Prevista TEXT, Canali TEXT, Contenuto TEXT, 
                  Link TEXT, Foto_Nome TEXT, Foto_Bytes BLOB, Assegnato_a TEXT, 
                  Stato TEXT, Completato_da TEXT, Data_Fine TEXT)''')
    
    # 2. Migrazione sicura per Titolo
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN Titolo TEXT DEFAULT 'Senza Titolo'")
    except sqlite3.OperationalError:
        pass # Colonna già esistente
        
    # 3. Migrazione sicura per Link (Risolve il tuo errore)
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN Link TEXT")
    except sqlite3.OperationalError:
        pass # Colonna già esistente

    c.execute('CREATE TABLE IF NOT EXISTS team (nome TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS canali (nome TEXT UNIQUE)')
    conn.commit()
    conn.close()
