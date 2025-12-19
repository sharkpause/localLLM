import threading
from enum import Enum, auto

from textual import events
from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Input, Markdown, Label, TextArea, Button
from textual.containers import VerticalScroll, Horizontal, Container, Vertical
from textual.binding import Binding

from localLLM import ollama

class InputMode(Enum):
    TYPING = auto()
    SUBMIT = auto()
    SIDEBAR = auto()
    MODEL_PICKER = auto()
    SETTINGS = auto()

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
            debug_log(f'index: {index}')
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
                self.app.sidebar.close_model_picker()
                event.stop()
    
    def selected_model(self) -> str:
        return self.models[self.cursor]

class SettingsPopup(Container):
    can_focus = True

    def __init__(self, items: list[str], **kwargs):
        super().__init__(**kwargs)
        self.items = items
        self.cursor = 0

    def on_mount(self):
        self.refresh_list()

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
        match event.key:
            case "up" | "k":
                self.move_cursor(-1)
            case "down" | "j":
                self.move_cursor(1)
            case "enter":
                self.app.activate_setting()
            case "escape":
                self.app.close_settings()

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
                text = f"[reverse]{text}[/reverse]"
        
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
                debug_log('enter')
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
                self.clear_cursor()
            case "settings":
                self.open_settings()
    
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

        self.close_model_picker()
    
    def close_model_picker(self):
        popup = getattr(self, "model_picker_popup", None)

        try:
            popup.remove()
        except Exception:
            for child in list(popup.children):
                child.remove()
            popup.remove()
        self.model_picker_popup = None
        self.app.update_mode(InputMode.SIDEBAR)

    def update_model_label(self, model_name: str):
        self.items['model'] = model_name
        self.refresh_list()

    def update_mode_label(self, mode: str):
        self.mode = mode
        self.refresh_list()

class ChatUI(App):
    CSS_PATH = "style.tcss"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.app_state = {
            'model_name': 'gemma3:4b',
            'conversation': []
        }

        self.messages = [
            { 'role': 'system', 'text': '# How may I help you today... or tonight?' },
        ]

        self.sidebar_items = [
            'model',
            'settings',
            'chats',
        ]

        self.sidebar_index = 0

        self.mode = InputMode.TYPING

    def compose(self):
        self.sidebar_items = {
            "mode": "TYPING",
            "model": self.app_state["model_name"],
            "settings": "Settings",
            "chats": "Chats",
        }

        self.sidebar = Sidebar(self.sidebar_items, id="sidebar")

        self.chat_view = VerticalScroll(
            Markdown(self.messages[0]["text"], id="conversation"),
            id="chat-section",
        )

        self.user_textarea = TextArea(placeholder="Type your message...", id="input-box")

        yield Horizontal(
            self.sidebar,
            Vertical(
                self.chat_view,
                Horizontal(self.user_textarea, id="input-section"),
            ),
        )

    def on_mount(self):
        self.query_one('#input-box').focus()
    
    def on_key(self, event) -> None:
        match event.key:
            case 'escape':
                self.change_to_submit(event)
            case 't':
                self.change_to_typing(event)
            case 's':
                if self.mode != InputMode.TYPING:
                    self.change_to_sidebar(event)
            case 'enter':
                if self.mode == InputMode.SUBMIT:
                    self.submit_message()
                    event.prevent_default()
            case 'q':
                if self.mode == InputMode.SUBMIT:
                    exit(0)
    
    def change_to_submit(self, event):
        self.update_mode(InputMode.SUBMIT)
        self.user_textarea.blur()
        self.update_mode_indicator()
        event.prevent_default()
        
        return
    
    def change_to_typing(self, event):
        self.update_mode(InputMode.TYPING)
        self.user_textarea.focus()
        self.user_textarea.blur()
        event.prevent_default()

        return

    def change_to_sidebar(self, event):
        self.sidebar.focus()
        self.update_mode(InputMode.SIDEBAR)
        self.user_textarea.blur()

    def submit_message(self):
        user_text = self.user_textarea.text.strip()

        if not user_text:
            return

        self.user_textarea.text = ""
        self.user_textarea.focus()

        user_message = {
            "role": "user",
            "text": f"\n\n{user_text}\n\n",
        }

        self.messages.append(user_message)
        self.render_messages(user_message)

        self.app_state["conversation"].append({
            "role": "user",
            "content": user_text,
        })

        assistant_message = {
            "role": "assistant",
            "text": "",
        }

        self.messages.append(assistant_message)
        self.render_messages(assistant_message)

        spinner_frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        # spinner_frames = ['-', '\\', '|', '/']
        spinner_index = 0
        spinner_running = True
        assistant_widget = self.chat_view.children[-1]

        def spinner_tick():
            nonlocal spinner_index
            assistant_widget.update(spinner_frames[spinner_index])
            spinner_index = (spinner_index + 1) % len(spinner_frames)

        spinner_timer = self.set_interval(0.1, spinner_tick)

        def stream_response():
            nonlocal spinner_running
            stream = ollama.chat(
                model=self.app_state["model_name"],
                messages=self.app_state["conversation"],
                stream=True,
            )

            full_response = ""

            for chunk in stream:
                text = chunk["message"].get("content", "")
                if not text:
                    continue

                if spinner_running:
                    spinner_running = False
                    spinner_timer.stop()

                full_response += text

                def update_ui():
                    assistant_message["text"] = full_response
                    assistant_widget.update(full_response)
                    self.chat_view.scroll_end(animate=False)

                self.call_from_thread(update_ui)

            self.app_state["conversation"].append({
                "role": "assistant",
                "content": full_response,
            })

        threading.Thread(target=stream_response, daemon=True).start()
        self.update_mode(InputMode.TYPING)
    
    def update_mode(self, mode):
        if self.mode == mode:
            return

        self.mode = mode
        self.update_mode_indicator()
        self.update_placeholder()

    def update_mode_indicator(self):
        label = self.sidebar.mode

        match self.mode:
            case InputMode.TYPING:
                self.sidebar.update_mode_label('TYPING')
            case InputMode.SUBMIT:
                self.sidebar.update_mode_label('SUBMIT')
            case InputMode.SIDEBAR:
                self.sidebar.update_mode_label('SIDEBAR')
                self.sidebar.apply_cursor()
            case InputMode.MODEL_PICKER:
                self.sidebar.update_mode_label('MODEL PICKER')
            case InputMode.SETTINGS:
                self.sidebar.update_mode_label('SETTINGS')
    
    def update_placeholder(self):
        if self.mode == InputMode.TYPING:
            self.user_textarea.placeholder = "Type your message…"
        else:
            self.user_textarea.placeholder = "Press Enter to send, t to edit"

    # def open_settings(self):
    #     self.sidebar.blur()

    #     self.settings_popup_container = Container(
    #         SettingsPopup(["Quit", "Change Model"]),
    #         id="settings-popup-container"
    #     )
    #     self.mount(self.settings_popup_container)

    #     self.set_focus(self.settings_popup_container.query_one(SettingsPopup))
    #     self.update_mode(InputMode.SETTINGS)

    # def close_settings(self):
    #     if hasattr(self, "settings_popup_container") and self.settings_popup_container:
    #         self.settings_popup_container.remove()
    #         self.settings_popup_container = None

    #     self.set_focus(self.sidebar)
    #     self.update_mode(InputMode.SIDEBAR)

    def render_messages(self, message):
        if message['role'] == "user":
            widget = Static(message['text'])
            widget.classes = "user-message"
            widget.styles.align_self = "end"

        elif message['role'] == "assistant":
            widget = Markdown(message['text'])
            widget.classes = "assistant-message"
            widget.styles.align_self = "start"

        else:  # system
            widget = Markdown(message['text'])
            widget.classes = "system-message"
            widget.styles.align_self = "center"

        self.chat_view.mount(widget)
        self.chat_view.scroll_end(animate=False)

def debug_log(msg: str):
    with open("debug_log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

if __name__ == "__main__":
    app = ChatUI()
    app.run()
