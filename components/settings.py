from textual.containers import Container
from textual.widgets import Static
from textual import events

from .input_mode import InputMode

class Settings(Container):
    can_focus = True

    def __init__(self, items: list[str], **kwargs):
        super().__init__(**kwargs)
        self.items = items
        self.cursor = 0

    def on_mount(self):
        self.refresh_list()
        self.focus()

    def refresh_list(self):
        for child in list(self.children):
            child.remove()

        for index, item in enumerate(self.items):
            text = item
            if index == self.cursor:
                text = f"[reverse]{item}[/reverse]"
            self.mount(Static(text))

    def move_cursor(self, delta: int):
        self.cursor = max(0, min(self.cursor + delta, len(self.items) - 1))
        self.refresh_list()

    def selected_item(self) -> str:
        return self.items[self.cursor]

    def on_key(self, event):
        key = event.key

        match key:
            case "up" | "k":
                self.move_cursor(-1)
                event.stop()
            case "down" | "j":
                self.move_cursor(1)
                event.stop()
            case "enter":
                self.app.activate_setting()
                event.stop()
            case "escape":
                self.app.close_settings(InputMode.SUBMIT)
                event.stop()
            case 't':
                self.app.close_settings(InputMode.TYPING)
                event.stop()
            case 's':
                self.app.close_settings(InputMode.SIDEBAR)
                event.stop()