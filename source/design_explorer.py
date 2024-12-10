# Copyright (c) 2024 texer.ai. All rights reserved.

import json

class DesignExplorer:
    # A class to explore and interact with a design hierarchy.

    def __init__(self):
        """Initializes an empty DesignExplorer instance."""
        self.files = []

    def load_design(self, json_file):
        """Loads the design hierarchy from a JSON file.

        Args:
            json_file (str): The path to the JSON file containing the design hierarchy.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            json.JSONDecodeError: If the JSON file is not properly formatted.
        """
        try:
            with open(json_file, 'r') as file:
                self.hierarchy = json.load(file)
        except FileNotFoundError as e:
            print(f"Error: File not found - {json_file}")
            raise e
        except json.JSONDecodeError as e:
            print(f"Error: Failed to decode JSON - {json_file}")
            raise e