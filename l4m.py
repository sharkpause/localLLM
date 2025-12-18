import threading

from textual.app import App, ComposeResult
from textual.widgets import Static, Input, Markdown, Label
from textual.containers import VerticalScroll, Horizontal

from localLLM import ollama

class ChatUI(App):
    CSS_PATH = "style.tcss"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cli_state = {
            'model_name': 'gemma3:4b',
            'conversation': []
        }

        self.messages = [
            { 'role': 'system', 'text': '# How may I help you today... or tonight?' },
        ]

    def compose(self) -> ComposeResult:
        self.chat_view = VerticalScroll(
            Markdown(self.messages[0]['text'], id='conversation'),
            id='chat-section'
        )
        yield self.chat_view
        
        self.user_input = Input(placeholder='Type your message...', id='input-box')
        yield self.user_input

    def on_mount(self):
        self.query_one('#input-box').focus()

    def on_input_submitted(self, event: Input.Submitted):
        user_text = event.value.strip()
        if not user_text:
            return

        self.query_one("#input-box").value = ""

        user_message = {
            'role': 'user',
            'text': f'\n\n{user_text}\n\n'
        }
        self.messages.append(user_message)
        self.render_messages(user_message)

        self.cli_state['conversation'].append({'role': 'user', 'content': user_text})
        # convo = self.query_one("#conversation", Markdown)
        # convo.update(self.build_chat_buffer())
        # def scroll_end():
        #     scroll = self.query_one(VerticalScroll)
        #     scroll.scroll_end(animate=False)
        #     # animate is set to False to prevent flickering

        # prefix = "\n\n**AI:** "

        # # spinner_running = True
        # # frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        # # i = 0

        # # def spin():
        # #     nonlocal i
        # #     convo.update(self.chat_buffer + "**AI:** " + frames[i % len(frames)])
        # #     i += 1

        # # spin_timer = self.set_interval(0.1, spin)

        
        # def stream_response():
        #     # nonlocal spinner_running

        #     stream = ollama.chat(
        #         model=self.cli_state['model_name'],
        #         messages=self.cli_state['conversation'],
        #         stream=True,
        #     )

        #     full_response = ''

        #     for chunk in stream:
        #         # if spinner_running:
        #         #     self.chat_buffer += f" **AI:** "
        #         #     spin_timer.stop()
        #         #     spinner_running = False

        #         text = chunk['message'].get("content", "")

        #         full_response += text

        #         self.messages += text
        #         self.call_from_thread(convo.update, self.chat_buffer)
        #         self.call_from_thread(scroll_end)

        #     self.cli_state['conversation'].append({
        #         'role': 'assistant',
        #         'content': full_response
        #     })

        # threading.Thread(target=stream_response, daemon=True).start()

    def render_messages(self, message):
        # convo_scroll = self.query_one("#chat-section", VerticalScroll)
        # for child in list(convo_scroll.children):
        #     child.remove()

        # for message in self.messages:
        #     match message['role']:
        #         case 'user':
        #             text_widget = Static(message['text'])
        #             text_widget.classes = 'user-message'
        #         case 'assistant':
        #             text_widget = Markdown(message['text'])
        #             text_widget.classes = 'assistant-message'
        #         case 'system':
        #             text_widget = Markdown(message['text'])
        #             text_widget.classes = 'system-message'
            
        #     convo_scroll.mount(text_widget)

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
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

if __name__ == "__main__":
    app = ChatUI()
    app.run()
