from textual.containers import Vertical, Container
from textual.widgets import Static
from textual import events

from .input_mode import InputMode
from .model_picker import ModelPicker
from .settings import Settings
from localLLM import ollama

class Sidebar(Vertical):
    can_focus = True

    def __init__(self, items: dict[str, str], **kwargs):
        super().__init__(**kwargs)

        self.mode = items['mode']
        
        self.items = {}
        for key, value in items.items():
            if key != 'mode':
                self.items[key] = value

        self.keys = list(self.items.keys())
        self.cursor = 0

        self.cursor_on = False

    def on_mount(self):
        self.refresh_list()

    def on_focus(self, event):
        if self.app.mode != InputMode.SIDEBAR:
            return
        
        self.refresh_list()

    def refresh_list(self):
        mode_classes = []
        match self.mode:
            case 'TYPING':
                mode_classes.append('typing')
            case 'SUBMIT':
                mode_classes.append('submit')
            case 'SIDEBAR':
                mode_classes.append('sidebar')
            case 'MODEL_PICKER':
                mode_classes.append('model-picker')
            case 'SETTINGS':
                mode_classes.append('settings')

        if len(self.children) > 0:
            mode_widget = self.children[0]
            mode_widget.update(self.mode)
            mode_widget.set_classes(mode_classes)
        else:
            mode_widget = Static(self.mode)
            mode_widget.set_classes(mode_classes)
            self.mount(mode_widget)

        for i, key in enumerate(self.keys):
            text = self.items[key]
            item_classes = []

            if i == self.cursor and self.cursor_on:
                text = f'[reverse]{text}[/reverse]'
        
            child_index = i + 1
            if child_index < len(self.children):
                widget = self.children[child_index]
                widget.update(text)
                widget.set_classes(item_classes)
            else:
                widget = Static(text)
                widget.set_classes(item_classes)
                self.mount(widget)

    def move_cursor(self, delta: int):
        self.cursor = (self.cursor + delta) % len(self.keys)

        self.refresh_list()
    
    def apply_cursor(self):
        self.cursor_on = True
    
    def clear_cursor(self):
        self.cursor_on = False

    def selected_item(self):
        return self.keys[self.cursor]

    def on_key(self, event):
        if not self.cursor_on:
            return

        match event.key:
            case "up" | "k":
                self.move_cursor(-1)
            case "down" | "j":
                self.move_cursor(1)
            case "enter":
                self.clear_cursor()
                self.activate_item()
            case "escape":
                self.clear_cursor()
                self.app.update_mode(InputMode.SUBMIT)
            case "t":
                self.clear_cursor()
                self.app.update_mode(InputMode.TYPING)
            case 'q':
                exit(0)

    def activate_item(self):
        item = self.selected_item()

        match item:
            case "model":
                self.open_model_picker()
            case "settings":
                self.open_settings()
        self.clear_cursor()
    
    def open_model_picker(self):
        models = [m.model for m in ollama.list().get("models", [])]

        self.model_picker_popup = Container(
            ModelPicker(models, id="model-picker"),
            id="model-picker-container",
        )
        self.mount(self.model_picker_popup)

        self.app.set_focus(self.model_picker_popup.query_one(ModelPicker))

        self.app.update_mode(InputMode.MODEL_PICKER)

    def pick_model(self, model_name: str):
        self.app.app_state["model_name"] = model_name

        self.update_model_label(model_name)

        self.close_model_picker(InputMode.SIDEBAR)
    
    def close_model_picker(self, input_mode):
        popup = getattr(self, "model_picker_popup", None)

        try:
            popup.remove()
        except Exception:
            for child in list(popup.children):
                child.remove()
            popup.remove()
        self.model_picker_popup = None
        self.app.update_mode(input_mode)

    def open_settings(self):
        self.blur()

        self.settings_container = Container(
            Settings(['Change preprompt']),
            id='settings-container'
        )
        self.mount(self.settings_container)

        self.app.set_focus(self.settings_container.query_one(Settings))
        self.app.update_mode(InputMode.SETTINGS)

    def close_settings(self, input_mode):
        if hasattr(self, 'settings_popup_container') and self.settings_container:
            self.settings_container.remove()
            self.settings_container = None

        self.app.set_focus(self.sidebar)
        self.app.update_mode(input_mode)

    def update_model_label(self, model_name: str):
        self.items['model'] = model_name
        self.refresh_list()

    def update_mode_label(self, mode: str):
        self.mode = mode
        self.refresh_list()