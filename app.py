from textual.app import App
from textual.binding import Binding
from textual.widgets import Header, Footer
from textual.screen import Screen
from ui import WelcomeScreen, EntriesCalendar, SearchScreen, MistakesScreen, BackupScreen, ExportScreen
import sqlite3
import os
import logging
import sys

# Set up logging to both file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('journal.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Print current directory and files for debugging
print(f"Current directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")

class JournalApp(App):
    """A terminal-based journal application."""
    
    TITLE = "Terminal Journal"
    SUB_TITLE = "A TUI Journal Application"
    CSS_PATH = "journal.css"
    
    SCREENS = {
        "calendar": "EntriesCalendar",  # Changed to string to avoid circular import
        "search": "SearchScreen",
        "mistakes": "MistakesScreen",
        "backup": "BackupScreen",
        "export": "ExportScreen",
    }
    
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]
    
    def __init__(self):
        super().__init__()
        self._init_database()
        
    def _init_database(self):
        """Initialize the database if it doesn't exist."""
        try:
            if not os.path.exists("journal.db"):
                logger.info("Creating new database")
                conn = sqlite3.connect("journal.db")
                cursor = conn.cursor()
                
                # Create entries table
                cursor.execute('''CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY,
                    date TEXT,
                    title TEXT,
                    description TEXT,
                    improvements TEXT,
                    setbacks TEXT,
                    mistakes TEXT
                )''')
                
                # Create mistakes table
                cursor.execute('''CREATE TABLE IF NOT EXISTS mistakes (
                    id INTEGER PRIMARY KEY,
                    mistake TEXT UNIQUE,
                    count INTEGER DEFAULT 1
                )''')
                
                conn.commit()
                conn.close()
                logger.info("Database created successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise
            
    def on_mount(self) -> None:
        """Called when app is mounted"""
        try:
            logger.info("App mounted successfully")
            self.push_screen(WelcomeScreen())
        except Exception as e:
            logger.error(f"Error during app mount: {str(e)}")
            raise
            
    def compose(self):
        """Create child widgets for the app."""
        try:
            logger.info("Starting to compose app widgets")
            yield Header()
            yield Footer()
            logger.info("App widgets composed successfully")
        except Exception as e:
            logger.error(f"Error composing widgets: {str(e)}", exc_info=True)
            raise

    def push_screen(self, screen: str | Screen, *args, **kwargs) -> None:
        """Override push_screen to handle string screen names."""
        if isinstance(screen, str):
            if screen in self.SCREENS:
                screen_class = getattr(self.screen_module, self.SCREENS[screen])
                screen = screen_class()
        super().push_screen(screen, *args, **kwargs)

    @property
    def screen_module(self):
        """Get the module containing screen classes."""
        import sys
        return sys.modules["ui"]

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()
        
    def action_push_screen(self, screen_name: str) -> None:
        """Push a screen onto the screen stack."""
        try:
            if screen_name == "search":
                self.push_screen(SearchScreen())
            elif screen_name == "mistakes":
                self.push_screen(MistakesScreen())
            elif screen_name == "backup":
                self.push_screen(BackupScreen())
            elif screen_name == "export":
                self.push_screen(ExportScreen())
        except Exception as e:
            logger.error(f"Error pushing screen {screen_name}: {str(e)}")
            self.notify(f"Error: {str(e)}", severity="error")

if __name__ == "__main__":
    try:
        print("Starting Journal Application...")
        print("Initializing app...")
        app = JournalApp()
        print("Running application...")
        app.run()
    except ImportError as e:
        logger.error(f"Import error: {str(e)}")
        print(f"Import Error: {str(e)}")
        print("Make sure all required packages are installed")
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        print(f"Database Error: {str(e)}")
        print("Check if journal.db is accessible")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        print(f"Error: {str(e)}")
        print("Check journal.log for more details")