import threading

from textual.app import App, ComposeResult
from textual.widgets import Static, Input
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

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static('How may I help you today... or tonight?', id='conversation')
        )

        
        yield Input(placeholder='Type your message...', id='input-box')

    def on_mount(self):
        self.query_one('#input-box').focus()

    def on_input_submitted(self, event: Input.Submitted):
        user_text = event.value.strip()
        if not user_text:
            return

        self.query_one('#input-box').value = ""

        convo = self.query_one("#conversation", Static)

        old = convo.content or ''
        new_text = f'{old}\nYou: {user_text}'

        convo.update(new_text)

        self.cli_state['conversation'].append({'role': 'user', 'content': user_text})

        def scroll_end():
            scroll = self.query_one(VerticalScroll)
            scroll.scroll_end(animate=False)

        base_content = convo.content
        frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        i = 0
        spinner_running = True

        def spin():
            nonlocal i
            convo.update(f'{base_content}\nAI: {frames[i % len(frames)]}')
            i += 1

        spin_timer = self.set_interval(0.1, spin)

        def stream_response():
            nonlocal spinner_running

            stream = ollama.chat(
                model=self.cli_state['model_name'],
                messages=self.cli_state['conversation'],
                stream=True,
            )

            prefix = '\nAI: '

            full_response = ""

            for chunk in stream:
                if spinner_running:
                    spin_timer.stop()
                    self.call_from_thread(convo.update, f'{base_content}{prefix}')

                    spinner_running = False
                
                if 'content' in chunk['message']:
                    text = chunk['message']['content']
                    if not text:
                        continue

                    full_response += text

                    self.call_from_thread(
                        convo.update,
                        f"{convo.content}{text}"
                    )

                    self.call_from_thread(scroll_end)
            self.cli_state['conversation'].append({
                'role': 'assistant',
                'content': full_response
            })

        threading.Thread(target=stream_response, daemon=True).start()


if __name__ == "__main__":
    app = ChatUI()
    app.run()
