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
        try:
            event.prevent_default()
        except Exception:
            pass

        key = event.key
        debug_log(f"ModelPicker key: {key}")
        match key:
            case "up" | "k":
                self.move_cursor(-1)
            case "down" | "j":
                self.move_cursor(1)
            case "enter":
                self.app.pick_model(self.selected_model())
            case "escape":
                self.app.close_model_picker()
    
    def selected_model(self) -> str:
        return self.models[self.cursor]

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
        self.sidebar_widgets = {
            'mode': Static("TYPING", id="mode-indicator"),
            "model": Static("gemma3:4b", id="sidebar-model"),
            "settings": Static("Settings", id="sidebar-settings"),
            "chats": Static("Chats", id="sidebar-chats"),
        }

        self.sidebar = Vertical(
            self.sidebar_widgets['mode'],
            self.sidebar_widgets['model'],
            self.sidebar_widgets['settings'],
            self.sidebar_widgets['chats'],

            id="sidebar",
        )

        self.chat_view = VerticalScroll(
            Markdown(self.messages[0]["text"], id="conversation"),
            id="chat-section",
        )

        self.user_textarea = TextArea(
            placeholder="Type your message...",
            id="input-box",
        )

        yield Horizontal(
            self.sidebar,
            Vertical(
                self.chat_view,
                Horizontal(
                    self.user_textarea,
                    id="input-section",
                ),
            ),
        )

    def on_mount(self):
        self.query_one('#input-box').focus()
    
    def on_key(self, event) -> None:
        if self.mode == InputMode.SIDEBAR:
            match event.key:
                case 'up' | 'k':
                    self.move_sidebar_cursor(-1)
                case 'down' | 'j':
                    self.move_sidebar_cursor(1)
                case 'enter':
                    self.activate_sidebar_item()
                case 'escape':
                    self.clear_sidebar_cursor()
                    self.update_mode(InputMode.SUBMIT)
                case 't':
                    self.clear_sidebar_cursor()
                    self.update_mode(InputMode.TYPING)

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
        self.update_mode(InputMode.SIDEBAR)
        self.user_textarea.blur()

        self.sidebar_index = 0
        self.apply_sidebar_cursor()

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

        # spinner_frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        spinner_frames = ['-', '\\', '|', '/']
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
        label = self.sidebar_widgets['mode']

        match self.mode:
            case InputMode.TYPING:
                label.update('TYPING')
                label.set_classes('typing')
            case InputMode.SUBMIT:
                label.update('SUBMIT')
                label.set_classes('submit')
            case InputMode.SIDEBAR:
                label.update('SIDEBAR')
                label.set_classes('sidebar')
            case InputMode.MODEL_PICKER:
                label.update('MODEL PICKER')
                label.set_classes('model-picker')  
    
    def update_placeholder(self):
        if self.mode == InputMode.TYPING:
            self.user_textarea.placeholder = "Type your message…"
        else:
            self.user_textarea.placeholder = "Press Enter to send, t to edit"

    def apply_sidebar_cursor(self):
        self.clear_sidebar_cursor()
        key = self.sidebar_items[self.sidebar_index]
        self.sidebar_widgets[key].add_class("cursor")

    def clear_sidebar_cursor(self):
        for widget in self.sidebar_widgets.values():
            widget.remove_class('cursor')

    def move_sidebar_cursor(self, delta: int):
        self.sidebar_index = (self.sidebar_index + delta) % len(self.sidebar_items)
        self.apply_sidebar_cursor()

    def activate_sidebar_item(self):
        item = self.sidebar_items[self.sidebar_index]

        match item:
            case 'model':
                self.open_model_picker()
                self.update_mode(InputMode.MODEL_PICKER)
    
    def open_model_picker(self):
        if getattr(self, "model_picker_popup", None) is not None:
            return

        if hasattr(self, "sidebar") and self.sidebar is not None:
            try:
                self.sidebar.blur()
            except Exception:
                pass

        models = []
        result = ollama.list()
        if 'models' in result:
            for model in result['models']:
                models.append(model.model)

        self.model_picker_popup = Container(
            ModelPicker(models, id="model-picker"),
            id="model-picker-container"
        )
        self.mount(self.model_picker_popup)

        picker = self.model_picker_popup.query_one(ModelPicker)
        if picker:
            try:
                self.set_focus(picker)
            except Exception:
                picker.focus()

        self.update_mode(InputMode.MODEL_PICKER)
    
    def close_model_picker(self):
        popup = getattr(self, "model_picker_popup", None)
        if not popup:
            return

        try:
            popup.remove()
        except Exception:
            try:
                for child in list(popup.children):
                    child.remove()
                popup.remove()
            except Exception:
                pass

        self.model_picker_popup = None

    def pick_model(self, model_name):
        self.app_state["model_name"] = model_name
    
        self.sidebar_widgets['model'].update(model_name)

        self.close_model_picker()

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
