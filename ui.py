from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Button, Label, Input, TextArea, DataTable, Static
from textual.widgets import RadioSet, RadioButton
from textual import events
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from rich.markdown import Markdown
from rich.panel import Panel
from rich.console import Console
from rich.table import Table
from rich.style import Style
from datetime import datetime, date
import calendar
import os
import sqlite3
import json

class JournalEntry:
    def __init__(self, id=None, date=None, title=None, description=None, improvements=None, setbacks=None, mistakes=None):
        self.id = id
        self.date = date
        self.title = title
        self.description = description
        self.improvements = improvements
        self.setbacks = setbacks
        self.mistakes = mistakes


class CalendarWidget(Grid):
    """A simplified and robust calendar widget compatible with Textual 0.52.1"""
    
    DEFAULT_CSS = """
    CalendarWidget {
        layout: grid;
        grid-size: 7;
        grid-rows: 7;
        grid-columns: 7;
        grid-gutter: 0;
        padding: 0;
        width: 100%;
        height: auto;
        background: $surface;
    }

    .calendar-day {
        text-style: none;
    }

    .calendar-day.disabled {
        background: $surface;
        color: $text-disabled;
        text-style: dim;
    }

    .calendar-day.future {
        color: $text-muted;
        text-style: italic;
    }

    .calendar-day.past {
        color: $text;
        text-style: none;
    }
    """
    
    def __init__(self, year=None, month=None):
        super().__init__()
        self.year = year or datetime.now().year
        self.month = month or datetime.now().month
        self.today = date.today()
        self.selected_date = None
        
    def compose(self) -> ComposeResult:
        # Add weekday headers
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for day in weekdays:
            yield Static(f" {day} ", classes="calendar-header")
            
        # Get the calendar for the month
        cal = calendar.monthcalendar(self.year, self.month)
        
        # Add day buttons
        for week in cal:
            for day in week:
                if day == 0:
                    yield Static("   ", classes="calendar-day empty")
                else:
                    current_date = date(self.year, self.month, day)
                    classes = ["calendar-day"]
                    
                    # Add date-specific classes
                    if current_date == self.today:
                        classes.append("today")
                    elif current_date > self.today:
                        classes.append("future")
                    else:
                        classes.append("past")
                        
                    button = Button(f" {day:2d} ", id=f"day_{day}", classes=" ".join(classes))
                    
                    # Add tooltips based on date
                    if current_date > self.today:
                        button.tooltip = "Live in present, Man!"
                    elif current_date < self.today:
                        button.tooltip = "Wanna add some nostalgic memories on this date you remember?"
                        
                    yield button
    
    def highlight_days_with_entries(self, dates_with_entries):
        """Highlight calendar days that have entries."""
        # Reset all days
        for button in self.query(".calendar-day"):
            if isinstance(button, Button):
                button.remove_class("has-entry")
                button.remove_class("disabled")
                
        # Add highlight class to days with entries and disable days without entries
        current_month_dates = set()
        for date_str in dates_with_entries:
            try:
                entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if entry_date.month == self.month and entry_date.year == self.year:
                    current_month_dates.add(entry_date.day)
                    day_button = self.query_one(f"#day_{entry_date.day}", Button)
                    if day_button:
                        day_button.add_class("has-entry")
            except (ValueError, AttributeError):
                continue
                
        # Disable buttons for days without entries (except today and future dates)
        for button in self.query(Button):
            if button.id and button.id.startswith("day_"):
                day = int(button.id.split("_")[1])
                current_date = date(self.year, self.month, day)
                
                if current_date < self.today and day not in current_month_dates:
                    button.add_class("disabled")
                    button.disabled = True

class EntriesCalendar(Screen):
    """Calendar view for navigating journal entries by date"""
    
    BINDINGS = [
        ("escape", "pop_screen", "Back"),
        ("q", "quit", "Quit"),
        ("left", "previous_month", "Previous Month"),
        ("right", "next_month", "Next Month"),
    ]
    
    def __init__(self):
        super().__init__()
        self.today = date.today()  # Add today's date
        self.year = self.today.year
        self.month = self.today.month
        
    def compose(self) -> ComposeResult:
        """Create child widgets for the calendar view."""
        yield Container(
            Container(
                Static(self._get_month_label(), id="month-label", classes="month-header"),
                CalendarWidget(self.year, self.month),
                Container(
                    Button("◀", id="prev-month", variant="primary"),
                    Button("▶", id="next-month", variant="primary"),
                    id="calendar-controls"
                ),
                id="calendar-container"
            ),
            Container(
                Static("", id="entry-preview"),
                id="preview-container"
            ),
            id="main-container"
        )
        yield Footer()
    
    def _get_month_label(self) -> str:
        """Get formatted month and year label."""
        return f"{calendar.month_name[self.month]} {self.year}"
    
    def on_mount(self) -> None:
        """Initialize the calendar when mounted."""
        self._highlight_days_with_entries()
        self._update_preview(self.today)  # Use self.today here
    
    def action_previous_month(self) -> None:
        """Handle previous month action."""
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1
        self._refresh_calendar()
    
    def action_next_month(self) -> None:
        """Handle next month action."""
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
        self._refresh_calendar()
    
    def action_pop_screen(self) -> None:
        """Return to the previous screen."""
        self.app.pop_screen()
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
    
    def _get_entries_for_month(self) -> list:
        """Get all dates with entries for current month."""
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT date FROM entries WHERE strftime('%Y-%m', date) = ?",
                    (f"{self.year}-{self.month:02d}",)
                )
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.notify(f"Database error: {str(e)}", severity="error")
            return []
    
    def _highlight_days_with_entries(self) -> None:
        """Update calendar to highlight days with entries."""
        calendar_widget = self.query_one(CalendarWidget)
        dates_with_entries = self._get_entries_for_month()
        calendar_widget.highlight_days_with_entries(dates_with_entries)
    
    def _refresh_calendar(self) -> None:
        """Refresh the calendar display."""
        # Update month label
        self.query_one("#month-label").update(self._get_month_label())
        
        # Replace calendar widget
        old_calendar = self.query_one(CalendarWidget)
        new_calendar = CalendarWidget(self.year, self.month)
        old_calendar.remove()
        calendar_container = self.query_one("#calendar-container")
        calendar_container.mount(new_calendar, before="#calendar-controls")
        
        # Update highlights and preview
        self._highlight_days_with_entries()
        self._update_preview(None)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "prev-month":
            self.action_previous_month()
        elif button_id == "next-month":
            self.action_next_month()
        elif button_id and button_id.startswith("day_"):
            day = int(button_id.split("_")[1])
            self._handle_day_selection(day)
    
    def _handle_day_selection(self, day: int) -> None:
        """Handle day selection in calendar."""
        selected_date = date(self.year, self.month, day)
        date_str = f"{self.year}-{self.month:02d}-{day:02d}"
        
        # If it's today's date, directly open create entry screen
        if selected_date == self.today:
            self.app.push_screen(CreateEntryScreen(date_str))
            return
            
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM entries WHERE date = ?", (date_str,))
                count = cursor.fetchone()[0]
                
            if count > 0:
                self.app.push_screen(DayEntriesScreen(date_str))
            else:
                self.app.push_screen(CreateEntryScreen(date_str))
                
        except sqlite3.Error as e:
            self.notify(f"Database error: {str(e)}", severity="error")
    
    def _update_preview(self, selected_date: date | None) -> None:
        """Update the entry preview panel."""
        preview = self.query_one("#entry-preview")
        
        if not selected_date:
            preview.update("")
            return
            
        date_str = selected_date.strftime("%Y-%m-%d")
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT title, description FROM entries WHERE date = ? ORDER BY id DESC LIMIT 1",
                    (date_str,)
                )
                entry = cursor.fetchone()
                
            if entry:
                title, description = entry
                preview_text = f"# {title}\n\n{description[:100]}..."
                preview.update(Panel(
                    Markdown(preview_text),
                    title=f"Entry for {date_str}",
                    border_style="green"
                ))
            else:
                preview.update(Panel(
                    f"No entries for {date_str}",
                    title="No Entry",
                    border_style="yellow"
                ))
                
        except sqlite3.Error as e:
            self.notify(f"Database error: {str(e)}", severity="error")
            preview.update("")


class DayEntriesScreen(Screen):
    """Screen for viewing entries for a specific day."""
    
    BINDINGS = [
        ("escape", "pop_screen", "Back"),
    ]
    
    def __init__(self, date_str: str):
        super().__init__()
        self.date_str = date_str
        
    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"Entries for {self.date_str}", classes="screen-title"),
            id="entries-container"
        )
        
    def on_mount(self) -> None:
        self._load_entries()
        
    def _load_entries(self):
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM entries WHERE date = ? ORDER BY id DESC",
                    (self.date_str,)
                )
                entries = cursor.fetchall()
                
            container = self.query_one("#entries-container")
            for entry in entries:
                container.mount(
                    Container(
                        Static(f"Title: {entry[2]}", classes="entry-title"),
                        Static(f"Description: {entry[3]}", classes="entry-section"),
                        Static(f"Improvements: {entry[4]}", classes="entry-section"),
                        Static(f"Setbacks: {entry[5]}", classes="entry-section"),
                        Static(f"Mistakes: {entry[6]}", classes="entry-section"),
                        classes="entry-card"
                    )
                )
        except sqlite3.Error as e:
            self.notify(f"Error loading entries: {str(e)}", severity="error")

    def action_pop_screen(self) -> None:
        """Return to the previous screen."""
        self.app.pop_screen()


class CreateEntryScreen(ModalScreen):
    """Screen for creating a new journal entry."""
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
    ]
    
    def __init__(self, date_str: str):
        super().__init__()
        self.date_str = date_str
        self.autosave_timer = None
        self.last_autosave = None
        self.is_dirty = False
        
    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"New Entry for {self.date_str}", classes="screen-title"),
            Label("Title"),
            Input(placeholder="Enter a title for your entry...", id="title"),
            Label("Description"),
            TextArea(id="description"),
            Label("Improvements"),
            TextArea(id="improvements"),
            Label("Setbacks"),
            TextArea(id="setbacks"),
            Label("Mistakes"),
            TextArea(id="mistakes"),
            Container(
                Static("Auto-saving enabled", id="autosave-status"),
                Button("Save", variant="primary", id="save"),
                Button("Cancel", id="cancel"),
                classes="button-container"
            ),
            classes="modal-content",
            id="entry-container"
        )
        
    def on_mount(self) -> None:
        """Set up auto-save when the screen is mounted."""
        # First create the tables
        self._create_settings_table()
        
        # Then set up auto-save
        self._setup_autosave()
        
        # Finally load any existing draft
        self._load_draft()
        
        # Set placeholder text for TextArea widgets
        self.query_one("#description").value = "Write about your day..."
        self.query_one("#improvements").value = "What did you do better today?"
        self.query_one("#setbacks").value = "What challenges did you face?"
        self.query_one("#mistakes").value = "What would you do differently?"
        
        # Add focus handlers to clear placeholder text
        self.query_one("#description").focus()
        self.query_one("#description").blur()
        self.query_one("#improvements").focus()
        self.query_one("#improvements").blur()
        self.query_one("#setbacks").focus()
        self.query_one("#setbacks").blur()
        self.query_one("#mistakes").focus()
        self.query_one("#mistakes").blur()
    
    def _create_settings_table(self):
        """Create the settings table if it doesn't exist."""
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                # Create settings table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                
                # Create drafts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS drafts (
                        date TEXT PRIMARY KEY,
                        content TEXT
                    )
                """)
                
                # Check if autosave_interval exists, if not add default value
                cursor.execute("SELECT value FROM settings WHERE key = 'autosave_interval'")
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?)",
                        ("autosave_interval", "5")
                    )
                
                conn.commit()
                
        except sqlite3.Error as e:
            self.notify(f"Error creating tables: {str(e)}", severity="error")
    
    def on_unmount(self) -> None:
        """Clean up auto-save timer when the screen is unmounted."""
        if self.autosave_timer:
            self.autosave_timer.stop()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        self.is_dirty = True
        self._update_autosave_status("Pending...")
    
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes."""
        self.is_dirty = True
        self._update_autosave_status("Pending...")
        
    def _setup_autosave(self):
        """Set up auto-save timer based on settings."""
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = 'autosave_interval'")
                result = cursor.fetchone()
                
            interval = int(result[0]) if result else 5  # Default to 5 minutes
            self.autosave_timer = self.set_interval(interval * 60, self._auto_save)
            self._update_autosave_status("Ready")
            
        except (sqlite3.Error, ValueError) as e:
            self.notify(f"Error setting up auto-save: {str(e)}", severity="error")
    
    def _auto_save(self):
        """Perform auto-save if content has changed."""
        if self.is_dirty:
            self._save_draft()
            self.is_dirty = False
            self._update_autosave_status("Saved")
    
    def _save_draft(self):
        """Save the current entry as a draft."""
        try:
            data = {
                "title": self.query_one("#title").value,
                "description": self.query_one("#description").value,
                "improvements": self.query_one("#improvements").value,
                "setbacks": self.query_one("#setbacks").value,
                "mistakes": self.query_one("#mistakes").value
            }
            
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO drafts (date, content)
                    VALUES (?, ?)
                """, (self.date_str, json.dumps(data)))
                
                conn.commit()
                
            self.last_autosave = datetime.now()
            
        except sqlite3.Error as e:
            self.notify(f"Error saving draft: {str(e)}", severity="error")
    
    def _load_draft(self):
        """Load any existing draft for this date."""
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT content FROM drafts WHERE date = ?", (self.date_str,))
                result = cursor.fetchone()
                
            if result:
                data = json.loads(result[0])
                self.query_one("#title").value = data.get("title", "")
                self.query_one("#description").value = data.get("description", "")
                self.query_one("#improvements").value = data.get("improvements", "")
                self.query_one("#setbacks").value = data.get("setbacks", "")
                self.query_one("#mistakes").value = data.get("mistakes", "")
                
                self.notify("Draft loaded", severity="information")
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            self.notify(f"Error loading draft: {str(e)}", severity="error")
    
    def _update_autosave_status(self, status: str):
        """Update the auto-save status display."""
        status_widget = self.query_one("#autosave-status")
        last_save = f" (Last: {self.last_autosave.strftime('%H:%M:%S')})" if self.last_autosave else ""
        status_widget.update(f"Auto-save: {status}{last_save}")
    
    def _save_entry(self):
        """Save the entry and clear the draft."""
        try:
            title = self.query_one("#title").value
            description = self.query_one("#description").value
            improvements = self.query_one("#improvements").value
            setbacks = self.query_one("#setbacks").value
            mistakes = self.query_one("#mistakes").value
            
            if not title.strip():
                self.notify("Title is required", severity="error")
                return
            
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO entries 
                    (date, title, description, improvements, setbacks, mistakes)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (self.date_str, title, description, improvements, setbacks, mistakes)
                )
                
                # Clear the draft after successful save
                cursor.execute("DELETE FROM drafts WHERE date = ?", (self.date_str,))
                conn.commit()
                
            self.notify("Entry saved successfully!", severity="success")
            
            # Get the parent calendar screen and refresh it
            calendar_screen = self.app.screen
            if isinstance(calendar_screen, EntriesCalendar):
                calendar_screen._highlight_days_with_entries()
                
            self.app.pop_screen()
            
        except sqlite3.Error as e:
            self.notify(f"Error saving entry: {str(e)}", severity="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save":
            self._save_entry()
        elif event.button.id == "cancel":
            self.app.pop_screen()
    
    def action_save(self) -> None:
        """Save the entry (Ctrl+S)."""
        self._save_entry()
        
    def action_cancel(self) -> None:
        """Cancel and close the screen."""
        self.app.pop_screen()


class SearchScreen(Screen):
    """Screen for searching journal entries."""
    
    BINDINGS = [
        ("escape", "pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Search Entries", classes="screen-title"),
            Input(placeholder="Search term...", id="search-input"),
            Static("", id="search-results"),
            classes="search-container"
        )
        
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self._perform_search(event.value)
            
    def _perform_search(self, term: str):
        if not term:
            self.query_one("#search-results").update("")
            return
            
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                query = """
                SELECT date, title, description 
                FROM entries 
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY date DESC
                """
                cursor.execute(query, (f"%{term}%", f"%{term}%"))
                results = cursor.fetchall()
                
            container = self.query_one("#search-results")
            container.remove_children()
            
            for date_str, title, description in results:
                container.mount(
                    Container(
                        Static(f"{date_str} - {title}", classes="entry-title"),
                        Static(description, classes="entry-section"),
                        classes="entry-card"
                    )
                )
                
        except sqlite3.Error as e:
            self.notify(f"Search error: {str(e)}", severity="error")

    def action_pop_screen(self) -> None:
        """Return to the previous screen."""
        self.app.pop_screen()


class MistakesScreen(Screen):
    """Screen for viewing mistake statistics."""
    
    BINDINGS = [
        ("escape", "pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Mistake Patterns", classes="screen-title"),
            Static("", id="mistakes-list"),
            classes="mistakes-container"
        )
        
    def on_mount(self) -> None:
        self._load_mistakes()
        
    def _load_mistakes(self):
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT mistake, count FROM mistakes ORDER BY count DESC"
                )
                mistakes = cursor.fetchall()
                
            container = self.query_one("#mistakes-list")
            for mistake, count in mistakes:
                container.mount(
                    Static(
                        f"[{count}x] {mistake}",
                        classes="mistake-item"
                    )
                )
                
        except sqlite3.Error as e:
            self.notify(f"Error loading mistakes: {str(e)}", severity="error")

    def action_pop_screen(self) -> None:
        """Return to the previous screen."""
        self.app.pop_screen()


class BackupScreen(Screen):
    """Screen for backing up journal data."""
    
    BINDINGS = [
        ("escape", "pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Backup Journal", classes="screen-title"),
            Button("Create Backup", id="backup", variant="primary"),
            Static("", id="backup-status"),
            classes="backup-container"
        )
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "backup":
            self._create_backup()
            
    def _create_backup(self):
        try:
            import shutil
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"journal_backup_{timestamp}.db"
            
            shutil.copy2("journal.db", backup_file)
            self.query_one("#backup-status").update(
                f"Backup created: {backup_file}"
            )
            self.notify("Backup created successfully!", severity="success")
            
        except Exception as e:
            self.notify(f"Backup error: {str(e)}", severity="error")

    def action_pop_screen(self) -> None:
        """Return to the previous screen."""
        self.app.pop_screen()


class ExportScreen(Screen):
    """Screen for exporting journal data."""
    
    BINDINGS = [
        ("escape", "pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Export Journal", classes="screen-title"),
            Button("Export to Markdown", id="export-md", variant="primary"),
            Button("Export to CSV", id="export-csv", variant="primary"),
            Static("", id="export-status"),
            classes="export-container"
        )
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "export-md":
            self._export_markdown()
        elif event.button.id == "export-csv":
            self._export_csv()
            
    def _export_markdown(self):
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT date, title, description, improvements, setbacks, mistakes FROM entries ORDER BY date"
                )
                entries = cursor.fetchall()
                
            with open("journal_export.md", "w") as f:
                for date_str, title, desc, imp, set, mist in entries:
                    f.write(f"# {title}\n\n")
                    f.write(f"Date: {date_str}\n\n")
                    f.write(f"## Description\n{desc}\n\n")
                    f.write(f"## Improvements\n{imp}\n\n")
                    f.write(f"## Setbacks\n{set}\n\n")
                    f.write(f"## Mistakes\n{mist}\n\n")
                    f.write("---\n\n")
                    
            self.notify("Exported to journal_export.md", severity="success")
            
        except Exception as e:
            self.notify(f"Export error: {str(e)}", severity="error")
            
    def _export_csv(self):
        try:
            import csv
            
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT date, title, description, improvements, setbacks, mistakes FROM entries ORDER BY date"
                )
                entries = cursor.fetchall()
                
            with open("journal_export.csv", "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Title", "Description", "Improvements", "Setbacks", "Mistakes"])
                writer.writerows(entries)
                
            self.notify("Exported to journal_export.csv", severity="success")
            
        except Exception as e:
            self.notify(f"Export error: {str(e)}", severity="error")

    def action_pop_screen(self) -> None:
        """Return to the previous screen."""
        self.app.pop_screen()

class SettingsScreen(Screen):
    """Screen for managing application settings."""
    
    BINDINGS = [
        ("escape", "pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Container(
            Static("Settings", classes="screen-title"),
            Container(
                Label("Theme"),
                RadioSet(
                    RadioButton("Dark", id="theme-dark"),
                    RadioButton("Light", id="theme-light"),
                    id="theme-selector"
                ),
                Label("Auto-save Interval (minutes)"),
                Input(value="5", id="autosave-interval"),
                Label("Default View"),
                RadioSet(
                    RadioButton("Calendar", id="default-calendar"),
                    RadioButton("Today's Entry", id="default-today"),
                    id="default-view"
                ),
                Label("Backup Settings"),
                Input(placeholder="Backup directory path...", id="backup-path"),
                RadioSet(
                    RadioButton("Daily", id="backup-daily"),
                    RadioButton("Weekly", id="backup-weekly"),
                    RadioButton("Monthly", id="backup-monthly"),
                    id="backup-frequency"
                ),
                classes="settings-group"
            ),
            Button("Save Settings", variant="primary", id="save-settings"),
            classes="settings-container"
        )
    
    def on_mount(self) -> None:
        """Load current settings when the screen is mounted."""
        self._load_settings()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-settings":
            self._save_settings()
    
    def _load_settings(self):
        """Load settings from the database."""
        try:
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                
                # Load existing settings
                cursor.execute("SELECT key, value FROM settings")
                settings = dict(cursor.fetchall())
                
                # Apply settings to UI
                if "theme" in settings:
                    self.query_one(f"#theme-{settings['theme']}", RadioButton).value = True
                if "autosave_interval" in settings:
                    self.query_one("#autosave-interval").value = settings["autosave_interval"]
                if "default_view" in settings:
                    self.query_one(f"#default-{settings['default_view']}", RadioButton).value = True
                if "backup_path" in settings:
                    self.query_one("#backup-path").value = settings["backup_path"]
                if "backup_frequency" in settings:
                    self.query_one(f"#backup-{settings['backup_frequency']}", RadioButton).value = True
                    
        except sqlite3.Error as e:
            self.notify(f"Error loading settings: {str(e)}", severity="error")
    
    def _save_settings(self):
        """Save settings to the database."""
        try:
            # Collect settings from UI
            theme = "dark" if self.query_one("#theme-dark").value else "light"
            autosave = self.query_one("#autosave-interval").value
            default_view = "calendar" if self.query_one("#default-calendar").value else "today"
            backup_path = self.query_one("#backup-path").value
            
            backup_frequency = "daily"
            for freq in ["daily", "weekly", "monthly"]:
                if self.query_one(f"#backup-{freq}").value:
                    backup_frequency = freq
                    break
            
            with sqlite3.connect("journal.db") as conn:
                cursor = conn.cursor()
                settings = {
                    "theme": theme,
                    "autosave_interval": autosave,
                    "default_view": default_view,
                    "backup_path": backup_path,
                    "backup_frequency": backup_frequency
                }
                
                for key, value in settings.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO settings (key, value)
                        VALUES (?, ?)
                    """, (key, value))
                    
                conn.commit()
                
            self.notify("Settings saved successfully!", severity="success")
            
        except sqlite3.Error as e:
            self.notify(f"Error saving settings: {str(e)}", severity="error")

    def action_pop_screen(self) -> None:
        """Return to the previous screen."""
        self.app.pop_screen()

class WelcomeScreen(Screen):
    """Welcome screen with keybindings for all features."""
    
    BINDINGS = [
        ("t", "create_today_entry", "Today's Entry"),
        ("c", "show_calendar", "Calendar"),
        ("n", "create_new_entry", "New Entry"),
        ("e", "edit_past_entries", "Edit Past Entry"),
        ("s", "show_search", "Search"),
        ("m", "show_mistakes", "Mistakes"),
        ("b", "show_backup", "Backup"),
        ("x", "show_export", "Export"),
        ("p", "show_settings", "Settings"),
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the welcome screen."""
        yield Container(
            Static("""[orange]
████████╗███████╗██████╗ ███╗   ███╗██╗███╗   ██╗ █████╗ ██╗     
╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║████╗  ██║██╔══██╗██║     
   ██║   █████╗  ██████╔╝██╔████╔██║██║██╔██╗ ██║███████║██║     
   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║██╔══██║██║     
   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║███████╗
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝
                                                                   
     ██╗ ██████╗ ██╗   ██╗██████╗ ███╗   ██╗ █████╗ ██╗          
     ██║██╔═══██╗██║   ██║██╔══██╗████╗  ██║██╔══██╗██║          
     ██║██║   ██║██║   ██║██████╔╝██╔██╗ ██║███████║██║          
██   ██║██║   ██║██║   ██║██╔══██╗██║╚██╗██║██╔══██║██║          
╚█████╔╝╚██████╔╝╚██████╔╝██║  ██║██║ ╚████║██║  ██║███████╗     
 ╚════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝     [/orange]""",
            classes="welcome-logo"),
            Static("[bold]Terminal Journal v1.0[/bold]", classes="welcome-version"),
            Static("", classes="welcome-spacer"),
            Static("""[bold]Quick Actions[/bold]

  [orange]t[/orange]  Create today's entry
  [orange]n[/orange]  Create entry for any date
  [orange]c[/orange]  Browse entries by date""", classes="welcome-primary-actions"),
            Static("""[bold]Journal Management[/bold]

  [orange]e[/orange]  Edit past entries
  [orange]s[/orange]  Search entries
  [orange]m[/orange]  View mistake patterns""", classes="welcome-secondary-actions"),
            Static("""[bold]Data Operations[/bold]

  [orange]b[/orange]  Create backup
  [orange]x[/orange]  Export journal
  [orange]q[/orange]  Quit Terminal Journal""", classes="welcome-tertiary-actions"),
            id="welcome-container"
        )
    
    def action_create_today_entry(self) -> None:
        """Create an entry for today's date."""
        today = date.today().strftime("%Y-%m-%d")
        self.app.push_screen(CreateEntryScreen(today))
    
    def action_create_new_entry(self) -> None:
        """Create a new entry for any date (opens calendar)."""
        self.app.push_screen(EntriesCalendar())
    
    def action_edit_past_entries(self) -> None:
        """Open calendar to edit past entries."""
        self.app.push_screen(EntriesCalendar())
    
    def action_show_calendar(self) -> None:
        """Show the calendar screen."""
        self.app.push_screen(EntriesCalendar())
    
    def action_show_search(self) -> None:
        """Show the search screen."""
        self.app.push_screen(SearchScreen())
    
    def action_show_mistakes(self) -> None:
        """Show the mistakes screen."""
        self.app.push_screen(MistakesScreen())
    
    def action_show_backup(self) -> None:
        """Show the backup screen."""
        self.app.push_screen(BackupScreen())
    
    def action_show_export(self) -> None:
        """Show the export screen."""
        self.app.push_screen(ExportScreen())
    
    def action_show_settings(self) -> None:
        """Show the settings screen."""
        self.app.push_screen(SettingsScreen())
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
