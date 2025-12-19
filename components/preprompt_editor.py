from pathlib import Path

from textual.containers import Container
from textual.widgets import TextArea, Label
from textual import events

from .input_mode import InputMode

PREPROMPT_PATH = Path('preprompt.txt')

class PrepromptEditor(Container):
    can_focus = True

    def on_mount(self):
        preprompt_text = ""

        if PREPROMPT_PATH.exists():
            preprompt_text = PREPROMPT_PATH.read_text(encoding="utf-8")

        self.title = Label("Edit preprompt (Ctrl+S to save, Esc to cancel)")
        self.textarea = TextArea(
            preprompt_text,
            id="preprompt-editor",
        )

        self.mount(self.title)
        self.mount(self.textarea)

        self.set_focus(self.textarea)

    def save(self):
        PREPROMPT_PATH.write_text(
            self.textarea.text,
            encoding="utf-8",
        )

    def on_key(self, event: events.Key):
        match event.key:
            case "escape":
                self.app.close_preprompt_editor(InputMode.SETTINGS)
                event.stop()

            case "ctrl+s":
                self.save()
                self.app.close_preprompt_editor(InputMode.SETTINGS)
                event.stop()
