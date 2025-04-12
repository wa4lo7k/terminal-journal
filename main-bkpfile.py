import sqlite3
from datetime import datetime

def create_entry():
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"Journal Entry for {today}"
    description = input("Enter today's description: ")
    improvements = input("What improvements did you make today? ")
    setbacks = input("What setbacks did you face? ")
    mistakes = input("Any mistakes to note? ")

    conn = sqlite3.connect("journal.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO entries (date, title, description, improvements, setbacks, mistakes) VALUES (?, ?, ?, ?, ?, ?)",
                   (today, title, description, improvements, setbacks, mistakes))

    conn.commit()
    conn.close()
    print("Journal entry saved successfully!")

create_entry()
#rich formatting
from rich.console import Console
from rich.table import Table

def show_entries():
    conn = sqlite3.connect("journal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entries")
    entries = cursor.fetchall()
    conn.close()

    console = Console()
    table = Table(title="Journal Entries")

    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Date", style="green")
    table.add_column("Title", style="blue")
    table.add_column("Description", style="yellow")

    for entry in entries:
        table.add_row(str(entry[0]), entry[1], entry[2], entry[3])

    console.print(table)

show_entries()
#store repeated mistakes daily
def store_mistake(mistake):
    conn = sqlite3.connect("journal.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO mistakes (mistake) VALUES (?)", (mistake,))
    conn.commit()
    conn.close()
#store mistakes
if mistakes:
    store_mistake(mistakes)
def export_to_markdown():
    with open("journal_export.md", "w") as file:
        conn = sqlite3.connect("journal.db")
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

export_to_markdown()

mistakes = input("Any mistakes to note? ").strip() or "None"


def store_mistake(mistake):
    conn = sqlite3.connect("journal.db")
    cursor = conn.cursor()
    
    # Check if mistake already exists
    cursor.execute("SELECT count FROM mistakes WHERE mistake = ?", (mistake,))
    result = cursor.fetchone()
    
    if result:
        # If mistake exists, increment the count
        new_count = result[0] + 1
        cursor.execute("UPDATE mistakes SET count = ? WHERE mistake = ?", (new_count, mistake))
    else:
        # If mistake does not exist, add it with count = 1
        cursor.execute("INSERT INTO mistakes (mistake, count) VALUES (?, ?)", (mistake, 1))
    
    conn.commit()
    conn.close()

def check_mistake_repetition(new_mistake):
    conn = sqlite3.connect("journal.db")
    cursor = conn.cursor()
    cursor.execute("SELECT mistake, count FROM mistakes")
    mistakes = cursor.fetchall()
    conn.close()

    for mistake, count in mistakes:
        if mistake == new_mistake and count > 2:  # Warn if repeated more than twice
            print(f"[ALERT] You've repeated this mistake {count} times! Time to make a change!")

if mistakes:
    store_mistake(mistakes)
    check_mistake_repetition(mistakes)
def search_entries(keyword):
    conn = sqlite3.connect("journal.db")
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
search_query = input("Search your journal (leave empty to skip): ")
if search_query:
    search_entries(search_query)
import os

def backup_to_github():
    os.system("git add .")
    os.system('git commit -m "Automated journal backup"')
    os.system("git push origin main")
    print("Journal backup completed!")
backup = input("Do you want to back up your journal to GitHub? (y/n): ").strip().lower()
if backup == 'y':
    backup_to_github()

