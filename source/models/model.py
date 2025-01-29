# Copyright (c) 2024 texer.ai. All rights reserved.
class DesignExplorerModel:
    def __init__(self):
        self.json_design_hierarchy = {}
        self.design_module_list = {}
        self.working_list = []
        self.working_list_ids = []
        self.command_buffer = ""

    def load_json_design_hierarchy(self, json_design_hierarchy):
        self.json_design_hierarchy = json_design_hierarchy
        i = 0
        for hierarchy, data in self.json_design_hierarchy.items():
            self.design_module_list[i] = hierarchy
            i += 1
        self.filter("")

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
        self.working_list_ids = []
        keyword_lower = keyword.lower()
        for id, item in self.design_module_list.items():
            if keyword_lower in item.lower():
                self.working_list_ids.append(id)
                self.working_list.append(item)

    def get_top_module(self, top_module_name):
        return self.json_design_hierarchy[top_module_name]
