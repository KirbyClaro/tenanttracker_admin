import sqlite3

def init_db():
    conn = sqlite3.connect('tenant_tracker.db')
    cursor = conn.cursor()

    # Created without the Emergency, Occupant, and Vehicle columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT DEFAULT 'Active',
            full_name TEXT NOT NULL,
            address TEXT,
            room_number TEXT,
            date_started TEXT,
            lease_term TEXT,
            move_out_date TEXT,
            monthly_due REAL,
            valid_id TEXT,
            job TEXT,
            messenger_link TEXT,
            email TEXT,
            contact_number TEXT,
            notes TEXT,
            agreement_signed INTEGER DEFAULT 0,
            advance_paid INTEGER DEFAULT 0,
            deposit_paid INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            amount REAL,
            due_date TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")