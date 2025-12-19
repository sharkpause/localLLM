from pathlib import Path

from textual.screen import Screen
from textual.containers import Container, Vertical
from textual.widgets import TextArea, Label
from textual import events

from .input_mode import InputMode

PREPROMPT_PATH = Path('preprompt.txt')

class PrepromptEditor(Screen):
    can_focus = True

    def compose(self):
        preprompt_text = ''
        if PREPROMPT_PATH.exists():
            preprompt_text = PREPROMPT_PATH.read_text(encoding='utf-8')

        self.textarea = TextArea(
            preprompt_text,
            id='preprompt-editor'
        )

        yield Vertical(
            Label(
                'Edit preprompt (Ctrl+S to save, Esc to cancel)',
                id='preprompt-editor-label'
            ),
            self.textarea,
            id='preprompt-editor-container'
        )

    def save(self):
        PREPROMPT_PATH.write_text(
            self.textarea.text,
            encoding='utf-8'
        )

    def on_key(self, event: events.Key):
        match event.key:
            case 'escape':
                self.dismiss()
                event.stop()
            case 'ctrl+s':
                self.save()
                self.dismiss()
                event.stop()
