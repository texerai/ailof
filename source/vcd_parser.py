# Copyright (c) 2024 texer.ai. All rights reserved.
import json
import os
import re

# Regex match constant strings.
REGEX_STRING_MATCH_MODULE = r"\$scope module (\S+) \$end"
REGEX_STRING_MATCH_STRUCT = r"\$scope struct (\S+) \$end"
REGEX_STRING_MATCH_INTERFACE = r"\$scope interface (\S+) \$end"
REGEX_STRING_MATCH_UNION = r"\$scope union (\S+) \$end"
REGEX_STRING_MATCH_VERILOG_MODULE_DECLARE = r"module\s+([^\s#(]+)"
REGEX_STRING_MATCH_VERILOG_ENTITY = r"(?<!module\s)\b([a-zA-Z_][a-zA-Z0-9_]*)\s+#\([\s\S]*?\)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+\("

# VCD related constants.
STRING_VCD_UNSCOPE = "$upscope $end"

# JSON object names.
JSON_OBJ_NAME_DECLARE_PATH = "declaration_path"
JSON_OBJ_NAME_MODULE_NAME = "module_name"


class VcdParser:
    # A class to parse VCD files and generate JSON about the design structure.
    def __init__(self):
        """Initializes an empty VcdParser instance."""
        self.design_info = {}
        self.hierarchy = {}

    def __validate_design_info(self, data):
        """Validates generated design_info. Private method used in 'parse' method"""
        keys = set(data.keys())

        for key in keys:
            parts = key.split(".")
            for i in range(1, len(parts)):
                splitted_key = ".".join(parts[:i])
                if splitted_key not in keys:
                    ancestor = ".".join(parts[: i - 1]) if i > 1 else ""
                    missing_module = parts[i - 1]
                    raise ModuleNotFoundError(f"Module '{missing_module}' is not found in {ancestor}")
        return True

    def parse(self, vcd_file_path, f_list):
        # Parses the VCD file and design files to generate a design hierarchy.
        if not os.path.isfile(vcd_file_path):
            raise FileNotFoundError(f"The file {vcd_file_path} does not exist.")

        # Generate hierarchy
        with open(vcd_file_path, "r") as vcd_file:
            lines = vcd_file.readlines()

        current_path = []
        skip_level = 0

        for line in lines:
            line = line.strip()

            scope_module_match = re.match(REGEX_STRING_MATCH_MODULE, line)
            scope_struct_match = re.match(REGEX_STRING_MATCH_STRUCT, line)
            scope_interface_match = re.match(REGEX_STRING_MATCH_INTERFACE, line)
            scope_union_match = re.match(REGEX_STRING_MATCH_UNION, line)

            if scope_module_match:
                if skip_level == 0:
                    module_name = scope_module_match.group(1)
                    current_path.append(module_name)

                    current_module = self.hierarchy
                    for path_part in current_path:
                        current_module = current_module.setdefault(path_part, {})

            elif scope_struct_match or scope_interface_match or scope_union_match:
                skip_level += 1

            elif line == STRING_VCD_UNSCOPE:
                if skip_level > 0:
                    skip_level -= 1
                elif current_path:
                    current_path.pop()

        # parse all modules and entities
        module_declarations = {}
        entity_to_class = {}
        entity_to_path = {}

        for line in f_list.splitlines():
            filepath = line.strip()

            if not os.path.isfile(filepath):
                print(f"File {filepath} not found.")
                continue

            try:
                with open(filepath, "r") as f:
                    content = f.read()

                    modules = re.findall(REGEX_STRING_MATCH_VERILOG_MODULE_DECLARE, content)

                    for module in modules:
                        module_declarations[module] = filepath

                    entities = re.findall(REGEX_STRING_MATCH_VERILOG_ENTITY, content)

                    for module_class, module_entity in entities:
                        entity_to_path[module_entity] = filepath
                        entity_to_class[module_entity] = module_class

            except Exception as e:
                print(f"Failed to read {filepath}: {e}")

        def process_node(node, current_path=""):
            for key, value in node.items():
                full_path = ""

                if module_declarations.get(key) is None and entity_to_path.get(key) is None:
                    full_path = f"{current_path}" if current_path else ""
                else:
                    full_path = f"{current_path}.{key}" if current_path else key

                self.design_info[full_path] = {
                    JSON_OBJ_NAME_DECLARE_PATH: None,
                    JSON_OBJ_NAME_MODULE_NAME: None,
                }

                if isinstance(value, dict):
                    process_node(value, full_path)

        process_node(self.hierarchy)

        for path, _ in self.design_info.items():
            module_name = path.split(".")[-1]

            if module_declarations.get(module_name) is not None:
                self.design_info[path][JSON_OBJ_NAME_DECLARE_PATH] = module_declarations.get(module_name)
                self.design_info[path][JSON_OBJ_NAME_MODULE_NAME] = module_name
                continue

            if entity_to_class.get(module_name) is not None:
                module_class = entity_to_class.get(module_name)
                if module_declarations.get(module_class) is not None:
                    self.design_info[path][JSON_OBJ_NAME_DECLARE_PATH] = module_declarations.get(module_class)
                    self.design_info[path][JSON_OBJ_NAME_MODULE_NAME] = module_class
                continue

        self.design_info = {path: data for path, data in self.design_info.items() if data[JSON_OBJ_NAME_DECLARE_PATH] is not None}

        self.__validate_design_info(self.design_info)
        return self.design_info

    def export_json(self, output_path):
        """Utility function. Exports the parsed design info as a JSON file."""
        with open(output_path, "w") as outfile:
            json.dump(self.design_info, outfile, indent=4)


if __name__ == "__main__":
    # Example usage
    parser = VcdParser()
