from textual import App, Container, Header, Footer, Button, Label, ScrollView, DataTable
from database import fetch_entries_by_month, fetch_entries_by_month_and_year
from datetime import datetime

class JournalApp(App):
    def __init__(self):
        super().__init__()
        self.entries_by_month = []
    
    def on_mount(self):
        self.entries_by_month = fetch_entries_by_month()

    async def on_button_pressed(self, button: Button):
        if button.id.startswith("month_card"):
            month_year = button.id.split("_")[-1]
            year, month = map(int, month_year.split("-"))
            self.push_screen(MonthEntriesScreen(self, year, month))
        elif button.id == "create_entry":
            self.push_screen(CreateEntryScreen(self))

    def render(self):
        month_cards = Container()
        for month_year, entry_count in self.entries_by_month:
            year, month = map(int, month_year.split("-"))
            month_name = datetime(year, month, 1).strftime('%B %Y')
            month_card = Button(f"{month_name} - {entry_count} entries", id=f"month_card_{month_year}", style="bold")
            month_cards.append(month_card)

        return Container(
            Header(),
            Footer(),
            month_cards,
            Button("Create Entry", id="create_entry", style="bold blue")
        )

class MonthEntriesScreen(App):
    def __init__(self, parent: App, year: int, month: int):
        super().__init__()
        self.parent = parent
        self.year = year
        self.month = month
        self.entries = fetch_entries_by_month_and_year(year, month)
    
    async def on_mount(self):
        entries_table = DataTable(columns=["ID", "Date", "Title", "Description"])
        for entry in self.entries:
            entries_table.add_row(entry[0], entry[1], entry[2], entry[3])
        
        scroll = ScrollView(entries_table)
        await self.view.dock(scroll)

    async def on_button_pressed(self, button: Button):
        if button.id == "back":
            self.app.pop_screen()

class CreateEntryScreen(App):
    def __init__(self, parent: App):
        super().__init__()
        self.parent = parent

    async def on_mount(self):
        self.view.dock(Label("Enter Journal Information:"), edge="top")
        self.view.dock(Button("Save Entry", id="save_entry", style="bold green"), edge="bottom")

    async def on_button_pressed(self, button: Button):
        if button.id == "save_entry":
            today = datetime.now().strftime("%Y-%m-%d")
            title = f"Journal Entry for {today}"
            description = input("Enter today's description: ")
            improvements = input("What improvements did you make today? ")
            setbacks = input("What setbacks did you face? ")
            mistakes = input("Any mistakes to note? ")

            # Save the new entry
            from database import insert_entry
            insert_entry(today, title, description, improvements, setbacks, mistakes)
            self.pop_screen()

    def render(self):
        return Container(
            Button("Back", id="back", style="red"),
        )

if __name__ == "__main__":
    JournalApp().run()

