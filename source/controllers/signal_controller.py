# Copyright (c) 2024 texer.ai. All rights reserved.
import sys
import termios
import tty

from source.enums import Command, ReturnCode


class SignalExplorerController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.keyword = ""
        self.running = True
        self.selected_signals = {}

    def read_key(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch += sys.stdin.read(2)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def process_key(self, key):
        ret_command = Command.UNDEFINED

        # Up.
        if key == "\x1b[A":
            ret_command = Command.UP
        # Down.
        elif key == "\x1b[B":
            ret_command = Command.DOWN
        # Ctrl+C.
        elif key == "\x03":
            ret_command = Command.TERMINATE
        # 1
        elif key == "1":
            ret_command = Command.SELECT_AND_GATE
        # 2
        elif key == "2":
            ret_command = Command.SELECT_OR_GATE
        # Enter/Space.
        elif key in ["\n", "\r", " "]:
            ret_command = Command.SELECT
        # Backspace.
        elif key == "\x7f":
            self.keyword = self.keyword[:-1]
            ret_command = Command.SEARCH
        # Ctrl+N.
        elif key == "\x0e":
            ret_command = Command.CONTINUE
        # Printable character.
        elif len(key) == 1 and key.isprintable():
            self.keyword += key
            ret_command = Command.SEARCH

        return ret_command

    def process_command(self, command):
        if command == Command.SEARCH:
            prev_actual_index = self.view.actual_index
            self.model.filter(self.keyword)
            if not self.keyword:
                target_index = min(prev_actual_index, len(self.model.working_list) - 1)
                self.view.page_number = target_index // self.view.display_width
                self.view.start_index = self.view.page_number * self.view.display_width
                self.view.end_index = (self.view.page_number + 1) * self.view.display_width
                self.view.highlighted_index = target_index % self.view.display_width
                self.view.actual_index = target_index
            self.view.update_view_data(self.model.working_list, self.model.working_list_ids)
        elif command == Command.UP:
            if self.view.actual_index > 0:
                self.view.highlighted_index -= 1
                self.view.actual_index -= 1
                if self.view.highlighted_index < 0:
                    self.view.page_number -= 1
                    self.view.start_index = self.view.page_number * self.view.display_width
                    self.view.end_index = (self.view.page_number + 1) * self.view.display_width
                    self.view.highlighted_index = self.view.display_width - 1
                    self.view.update_view_data(self.model.working_list, self.model.working_list_ids)
        elif command == Command.DOWN:
            if self.view.actual_index < len(self.model.working_list) - 1:
                self.view.highlighted_index += 1
                self.view.actual_index += 1
                if self.view.highlighted_index >= self.view.display_width:
                    self.view.page_number += 1
                    self.view.start_index = self.view.page_number * self.view.display_width
                    self.view.end_index = (self.view.page_number + 1) * self.view.display_width
                    self.view.highlighted_index = 0
                    self.view.update_view_data(self.model.working_list, self.model.working_list_ids)
        elif (command == Command.SELECT_AND_GATE) or (command == Command.SELECT):
            if not self.view.view_data:
                return
            current_id = self.view.view_data[self.view.highlighted_index]["id"]
            if current_id not in self.view.selected_and_ids:
                if current_id in self.view.selected_or_ids:
                    self.view.selected_or_ids.remove(current_id)
                self.view.selected_and_ids.append(current_id)
            else:
                self.view.selected_and_ids.remove(current_id)
        elif command == Command.SELECT_OR_GATE:
            if not self.view.view_data:
                return
            current_id = self.view.view_data[self.view.highlighted_index]["id"]
            if current_id not in self.view.selected_or_ids:
                if current_id in self.view.selected_and_ids:
                    self.view.selected_and_ids.remove(current_id)
                self.view.selected_or_ids.append(current_id)
            else:
                self.view.selected_or_ids.remove(current_id)
        elif command == Command.CONTINUE:
            if len(self.view.selected_and_ids) + len(self.view.selected_or_ids) > 0:
                self.running = False
                for id in self.view.selected_and_ids:
                    signal = self.model.selected_signals[id].split(" | ")[0]
                    self.selected_signals[signal] = {"signal_info": self.model.all_signals[signal], "gate_type": "&"}
                for id in self.view.selected_or_ids:
                    signal = self.model.selected_signals[id].split(" | ")[0]
                    self.selected_signals[signal] = {"signal_info": self.model.all_signals[signal], "gate_type": "|"}
        elif command == Command.TERMINATE:
            self.running = False
            return ReturnCode.TERMINATE
        else:
            print("Error: Unknown command.")
            return ReturnCode.FAILURE
        return ReturnCode.SUCCESS

    def run(self):
        self.view.print_message()
        self.read_key()
        self.view.update_view_data(self.model.working_list, self.model.working_list_ids)

        while self.running:
            self.view.update_view(self.keyword)
            key = self.read_key()
            command = self.process_key(key)
            return_code = self.process_command(command)
            if return_code == ReturnCode.TERMINATE:
                break

        return self.selected_signals, return_code
