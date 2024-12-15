# Copyright (c) 2024 texer.ai. All rights reserved.
import json

class DesignExplorerModel:
    def __init__(self):
        self.json_design_hierarchy = {}
        self.design_module_list = []
        self.working_list = []
        self.command_buffer = ""

    def load_json_design_hierarchy(self, json_design_hierarchy):
        self.json_design_hierarchy = json_design_hierarchy
        for hierarchy, data in self.json_design_hierarchy.items():
            self.design_module_list.append(hierarchy)

    def get_model_range(self, start, end):
        if start >= end:
            return []
        if start < 0 or end < 0:
            return []
        if start >= len(self.design_module_list):
            return []

        if end > len(self.design_module_list):
            end = len(self.design_module_list)

        return self.design_module_list[start:end]

    def register_key(self, key):
        self.search_buffer += key

    def filter(self, keyword):
        self.working_list = []
        for item in self.design_module_list:
            if keyword in item:
                self.working_list.append(item)
