import sqlite3
from datetime import datetime

# Connect to SQLite database
def connect_db():
    return sqlite3.connect('journal.db')

# Create necessary tables
def create_tables():
    conn = connect_db()
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

    # Commit and close the connection
    conn.commit()
    conn.close()

    print("Tables created successfully!")

# Insert a journal entry into the 'entries' table
def insert_entry(date, title, description, improvements, setbacks, mistakes):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO entries (date, title, description, improvements, setbacks, mistakes) VALUES (?, ?, ?, ?, ?, ?)",
                   (date, title, description, improvements, setbacks, mistakes))
    conn.commit()
    conn.close()
    print("Journal entry saved successfully!")

# Fetch journal entries grouped by month (Year-Month format)
def fetch_entries_by_month():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT strftime('%Y-%m', date) AS month, COUNT(*) AS entry_count 
                      FROM entries 
                      GROUP BY month 
                      ORDER BY month DESC''')
    entries_by_month = cursor.fetchall()
    conn.close()
    return entries_by_month

# Fetch journal entries for a specific month and year
def fetch_entries_by_month_and_year(year, month):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM entries WHERE strftime('%Y-%m', date) = ? ORDER BY date DESC''', (f'{year}-{month:02}',))
    entries = cursor.fetchall()
    conn.close()
    return entries

# Fetch all journal entries
def fetch_all_entries():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entries ORDER BY date DESC')
    entries = cursor.fetchall()
    conn.close()
    return entries

# Insert or update mistakes, with count tracking
def store_mistake(mistake):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO mistakes (mistake) VALUES (?)", (mistake,))
    cursor.execute("SELECT count FROM mistakes WHERE mistake = ?", (mistake,))
    result = cursor.fetchone()

    if result:
        new_count = result[0] + 1
        cursor.execute("UPDATE mistakes SET count = ? WHERE mistake = ?", (new_count, mistake))

    conn.commit()
    conn.close()
    print(f"Mistake '{mistake}' stored/updated successfully!")

# Fetch all stored mistakes and their counts
def fetch_mistakes():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM mistakes ORDER BY count DESC')
    mistakes = cursor.fetchall()
    conn.close()
    return mistakes

# Delete journal entries with no description (empty descriptions)
def delete_empty_entries():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM entries WHERE description = '';")
    conn.commit()
    conn.close()
    print("Deleted empty journal entries.")

# Delete entries older than a specific year and month
def delete_entries_before(year, month):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''DELETE FROM entries WHERE strftime('%Y-%m', date) < ?''', (f'{year}-{month:02}',))
    conn.commit()
    conn.close()
    print(f"Deleted journal entries before {year}-{month:02}.")

# Search journal entries across different fields
def search_entries(keyword):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entries WHERE title LIKE ? OR description LIKE ? OR improvements LIKE ? OR setbacks LIKE ? OR mistakes LIKE ?", 
                   (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
    results = cursor.fetchall()
    conn.close()

    if results:
        print("\n[Search Results]")
        for entry in results:
            print(f"\nDate: {entry[1]}\nTitle: {entry[2]}\nDescription: {entry[3]}\n")
    else:
        print("No entries found for that keyword.")

# Backup journal data to a Markdown file
def export_to_markdown():
    with open("journal_export.md", "w") as file:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM entries")
        entries = cursor.fetchall()
        conn.close()

        for entry in entries:
            file.write(f"## {entry[2]} ({entry[1]})\n")
            file.write(f"**Description:** {entry[3]}\n\n")
            file.write(f"**Improvements:** {entry[4]}\n\n")
            file.write(f"**Setbacks:** {entry[5]}\n\n")
            file.write(f"**Mistakes:** {entry[6]}\n\n")
            file.write("---\n")

    print("Journal exported as Markdown!")

# Initialize the database (create tables if they do not exist)
create_tables()

