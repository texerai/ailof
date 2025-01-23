# Copyright (c) 2024 texer.ai. All rights reserved.
import math
import sys


class DesignExplorerTerminalView:
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

    # Function to update the view data.
    def update_view_data(self, working_list, working_list_ids):
        self.view_data = []
        for i in range(self.start_index, self.end_index):
            if i < len(working_list):
                self.view_data.append(
                    {
                        "id": working_list_ids[i],
                        "hierarchy": working_list[i],
                    }
                )

        self.working_list_size = len(working_list)
        self.total_pages = self.working_list_size / self.display_width

    # Function to display the list with the selected item highlighted.
    def update_view(self, keyword):
        sys.stdout.write("\x1b[2J\x1b[H")
        print("\nSearch: " + keyword, end="", flush=True)
        print("\n===================\n")
        i = 0
        for data in self.view_data:
            if data["id"] in self.selected_ids:
                line_to_print = "{}. [x] {}".format(data["id"], data["hierarchy"])
            else:
                line_to_print = "{}. [ ] {}".format(data["id"], data["hierarchy"])

            if i == self.highlighted_index:
                print(f"--> {line_to_print}")  # Highlight the selected item
            else:
                print(f"    {line_to_print}")
            i += 1
        print(f"\n=================== Page {self.page_number}/{math.ceil(self.total_pages) - 1}")
        print("Commands: Enter/space key to select the module | Ctrl+c to exit | Ctrl+n to pass module info further")

    def register_command(self, command):
        pass

    # Function to display intro message.
    def print_intro(self):
        print("Ailof: AI assisted Logic Fuzzer. Texer.ai Ltd. (c) 2024.\n")
        print("The design is successfully parsed.")
        print("Select the modules in your design you would like to fuzz.\n")
        print("Press any key to start.")
        print("")
