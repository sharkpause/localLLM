import threading

from textual.app import App, ComposeResult
from textual.widgets import Static, Input, Markdown
from textual.containers import VerticalScroll

from localLLM import ollama

class ChatUI(App):
    def __init__(self, **kwargs):
        # call the parent constructor first
        super().__init__(**kwargs)

        self.cli_state = {
            'model_name': 'gemma3:4b',
            'conversation': []
        }

        self.chat_buffer = 'How may I help you today... or tonight?'

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Markdown(self.chat_buffer, id='conversation')
        )

        
        yield Input(placeholder='Type your message...', id='input-box')

    def on_mount(self):
        self.query_one('#input-box').focus()

    def on_input_submitted(self, event: Input.Submitted):
        user_text = event.value.strip()
        if not user_text:
            return

        self.query_one("#input-box").value = ""

        # maintain your own conversation buffer (init this earlier in your class)
        self.chat_buffer += f"\n\n**You:** {user_text}\n\n"

        convo: Markdown = self.query_one("#conversation", Markdown)
        convo.update(self.chat_buffer)

        self.cli_state['conversation'].append({'role': 'user', 'content': user_text})

        def scroll_end():
            scroll = self.query_one(VerticalScroll)
            scroll.scroll_end(animate=False)

        prefix = "\n\n**AI:** "

        spinner_running = True
        frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        i = 0

        def spin():
            nonlocal i
            convo.update(self.chat_buffer + "**AI:**" + frames[i % len(frames)])
            i += 1

        spin_timer = self.set_interval(0.1, spin)

        def stream_response():
            nonlocal spinner_running

            stream = ollama.chat(
                model=self.cli_state['model_name'],
                messages=self.cli_state['conversation'],
                stream=True,
            )

            full_response = ''

            for chunk in stream:
                if spinner_running:
                    self.chat_buffer += f" **AI:** "
                    spin_timer.stop()
                    spinner_running = False

                text = chunk['message'].get("content", "")

                full_response += text

                # append to buffer & update widget
                self.chat_buffer += text
                self.call_from_thread(convo.update, self.chat_buffer)
                self.call_from_thread(scroll_end)

            self.cli_state['conversation'].append({
                'role': 'assistant',
                'content': full_response
            })

        threading.Thread(target=stream_response, daemon=True).start()


if __name__ == "__main__":
    app = ChatUI()
    app.run()
