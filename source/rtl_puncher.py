# Copyright (c) 2024 texer.ai. All rights reserved.

class RtlPuncher:
    def __init__(self, json_design_hierarchy, selected_modules):
        self.json_design_hierarchy = json_design_hierarchy
        self.selected_modules = selected_modules

    def punch(self):
        for module in self.selected_modules:
            instances = module.split(".")
            design_files = {}
            seperator = ""
            hierarchy = ""
            for instance in instances:
                hierarchy += seperator + instance
                module_declaration_path = self.json_design_hierarchy[hierarchy]["declaration_path"]
                design_files[hierarchy] = module_declaration_path
                seperator = "."
                print(f"{hierarchy}\n    {module_declaration_path}")