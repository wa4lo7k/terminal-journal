import sqlite3

def create_tables():
    # Connect to SQLite database (creates 'journal.db' if it doesn't exist)
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()

    # Create a table for journal entries
    cursor.execute('''CREATE TABLE IF NOT EXISTS entries (
                        id INTEGER PRIMARY KEY,
                        date TEXT,
                        title TEXT,
                        description TEXT,
                        improvements TEXT,
                        setbacks TEXT,
                        mistakes TEXT)''')

    # Create the 'mistakes' table (only define it once)
    cursor.execute('''CREATE TABLE IF NOT EXISTS mistakes (
                        id INTEGER PRIMARY KEY,
                        mistake TEXT UNIQUE,
                        count INTEGER DEFAULT 1)''')

    # Delete empty journal entries automatically
    cursor.execute("DELETE FROM entries WHERE description = '';")

    # Commit and close the connection
    conn.commit()
    conn.close()

# Run the function
create_tables()

