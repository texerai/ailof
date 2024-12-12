# Copyright (c) 2024 texer.ai. All rights reserved.
import sys
from controllers.terminal_controller import Command

class DesignExplorerTerminalView:
    def __init__(self):
        self.display_width = 10
        self.highlighted_index = 0
        self.start_index = 0
        self.end_index = self.display_width
        self.actual_index = 0
        self.selected_indicies = []
        self.working_list_size = 0
        self.page_number = 0
        for i in range(self.display_width):
            self.selected_indicies.append(False)

    # Function to display the list with the selected item highlighted
    def update_view(self, working_list, keyword):
        self.working_list_size = len(working_list)
        sys.stdout.write("\x1b[2J\x1b[H")  # Clear the screen and move the cursor to the top
        print("\nSearch: " + keyword, end="", flush=True)  # Show command prompt
        print("\n===================\n")
        for i, item in enumerate(working_list[self.start_index:self.end_index]):
            item_number = self.display_width * self.page_number + i
            if self.selected_indicies[i]:
                line_to_print = "{}. [x] {}".format(item_number, item)
            else:
                line_to_print = "{}. [ ] {}".format(item_number, item)

            if i == self.highlighted_index:
                print(f"--> {line_to_print}")  # Highlight the selected item
            else:
                print(f"    {line_to_print}")
        print("\n===================")
        print("Commands: Ctrl+C to Exit | Enter to select the module")

    def register_command(self, command):
        if command == Command.UP:
            self.highlighted_index -= 1 % self.display_width
            self.actual_index
        elif command == Command.DOWN:
            self.highlighted_index += 1 % self.display_width
        elif command == Command.SELECT:
            self.selected_indicies[self.highlighted_index] = not self.selected_indicies[self.highlighted_index]

    # Function to display intro message.
    def print_intro(self):
        print("Ailof: AI assisted Logic Fuzzer. Texer.ai Ltd. (c) 2024.\n")
        print("The design is successfully parsed.")
        print("Select the modules in your design you would like to fuzz.\n")
        print("Press Enter to start.")
        print("")
