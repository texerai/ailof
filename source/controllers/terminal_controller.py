# Copyright (c) 2024 texer.ai. All rights reserved.
import enum
import sys
import termios
import tty

class Command(enum.Enum):
    UNDEFINED = 0
    UP = 1
    DOWN = 2
    TERMINATE = 3
    SELECT = 4
    SEARCH = 5

class DesignExplorerController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.keyword = ""
        self.running = True

    def read_key(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch += sys.stdin.read(2)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def process_key(self, key):
        ret_command = Command.UNDEFINED

        # Up.
        if key == '\x1b[A':
            ret_command = Command.UP
        # Down.
        elif key == '\x1b[B':
            ret_command = Command.DOWN
        # Ctrl+C.
        elif key == '\x03':
            ret_command = Command.TERMINATE
        # Enter/Space.
        elif key in ['\n', '\r', ' ']:
            ret_command = Command.SELECT
        # Backspace.
        elif key == '\x7f':
            self.keyword = self.keyword[:-1]
            ret_command = Command.SEARCH
        # Printable character.
        elif len(key) == 1 and key.isprintable():
            self.keyword += key
            ret_command = Command.SEARCH

        return ret_command

    def run(self):
        self.view.print_intro()
        self.model.load_dummy_data()
        self.read_key()
        self.view.update_view(self.model.working_list, "")

        while self.running:
            key = self.read_key()
            command = self.process_key(key)

            if command == Command.SEARCH:
                self.model.filter(self.keyword)
            elif command == Command.TERMINATE:
                self.running = False


            self.view.register_command(command)
            self.view.update_view(self.model.working_list, self.keyword)