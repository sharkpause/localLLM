import threading
from enum import Enum, auto

from textual import events
from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Input, Markdown, Label, TextArea, Button
from textual.containers import VerticalScroll, Horizontal, Container, Vertical
from textual.binding import Binding

from localLLM import ollama

from components.debug_log import debug_log
from components.input_mode import InputMode
from components.sidebar import Sidebar

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

if __name__ == "__main__":
    app = ChatUI()
    app.run()
