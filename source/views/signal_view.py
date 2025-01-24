# Copyright (c) 2024 texer.ai. All rights reserved.
import math
import sys


class SignalExplorerTerminalView:
    def __init__(self):
        self.display_width = 10
        self.highlighted_index = 0
        self.start_index = 0
        self.end_index = self.display_width
        self.actual_index = 0
        self.selected_ids = []
        self.view_data = []
        self.working_list_size = 0
        self.page_number = 0
        self.total_pages = 0

    def update_view_data(self, working_list, working_list_ids):
        self.view_data = []
        for i in range(self.start_index, self.end_index):
            if i < len(working_list):
                self.view_data.append(
                    {
                        "id": working_list_ids[i],
                        "signal": working_list[i],
                    }
                )

        self.working_list_size = len(working_list)
        self.total_pages = self.working_list_size / self.display_width

    def update_view(self, keyword):
        sys.stdout.write("\x1b[2J\x1b[H")
        print("\nSearch: " + keyword, end="", flush=True)
        print("\n===================\n")
        i = 0
        for data in self.view_data:
            if data["id"] in self.selected_ids:
                line_to_print = "{}. [x] {}".format(data["id"], data["signal"])
            else:
                line_to_print = "{}. [ ] {}".format(data["id"], data["signal"])

            if i == self.highlighted_index:
                print(f"--> {line_to_print}")  # Highlight the selected item
            else:
                print(f"    {line_to_print}")
            i += 1
        print(f"\n=================== Page {self.page_number}/{math.ceil(self.total_pages) - 1}")
        print("Commands: Enter/space key to select the signal | Ctrl+c to exit | Ctrl+n to pass signal info further")

    def print_message(self):
        print("Now, select the signals you would like to fuzz.\n")
        print("Press any key to proceed.")
        print("")
