from textual.widget import Widget
from textual.widgets import Static
from textual import events

from .input_mode import InputMode

class ModelPicker(Widget):
    can_focus = True

    def __init__(self, models: list[str], **kwargs):
        super().__init__(**kwargs)
        self.models = models
        self.cursor = 0

    def on_mount(self):
        self.refresh_list()
        self.focus()

    def refresh_list(self):
        for child in list(self.children):
            child.remove()

        for index, model in enumerate(self.models):
            text = model
            if index == self.cursor:
                text = f"[reverse]{model}[/reverse]"
            self.mount(Static(text))

    def move_cursor(self, delta: int):
        self.cursor = max(0, min(self.cursor + delta, len(self.models) - 1))
        self.refresh_list()

    def on_key(self, event):
        key = event.key

        match key:
            case "up" | "k":
                self.move_cursor(-1)
            case "down" | "j":
                self.move_cursor(1)
            case "enter":
                self.app.sidebar.pick_model(self.selected_model())
                event.stop()
            case "escape":
                self.app.sidebar.close_model_picker(InputMode.SUBMIT)
                event.stop()
            case 't':
                self.app.sidebar.close_model_picker(InputMode.TYPING)
                event.stop()
            case 's':
                self.app.sidebar.close_model_picker(InputMode.SIDEBAR)
                event.stop()
    
    def selected_model(self) -> str:
        return self.models[self.cursor]