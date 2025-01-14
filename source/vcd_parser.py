# Copyright (c) 2024 texer.ai. All rights reserved.
import json
import os
import re


# Regex match constant strings.
REGEX_STRING_MATCH_MODULE = r"\$scope module (\S+) \$end"
REGEX_STRING_MATCH_STRUCT = r"\$scope struct (\S+) \$end"
REGEX_STRING_MATCH_INTERFACE = r"\$scope interface (\S+) \$end"
REGEX_STRING_MATCH_UNION = r"\$scope union (\S+) \$end"
REGEX_STRING_MATCH_SIGNAL = r"\$var wire\s+(\d+)\s+\S+\s+([\w\[\]]+)(?:\s+\[\d+:\d+\])?\s+\$end"
REGEX_STRING_MATCH_VERILOG_MODULE_DECLARE = r"^\s*module\s+([^\s#(]+)"
REGEX_STRING_MATCH_VERILOG_ENTITY = r"^\s*(\w+)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s+(\w+)\s*\("

# VCD related constants.
STRING_VCD_UNSCOPE = "$upscope $end"

# JSON object names.
JSON_OBJ_NAME_DECLARE_PATH = "declaration_path"
JSON_OBJ_NAME_MODULE_NAME = "module_name"
JSON_OBJ_NAME_SIGNALS = "signal_width_data"


class VcdParser:
    # A class to parse VCD files and generate JSON about the design structure.
    def __init__(self):
        """Initializes an empty VcdParser instance."""
        self.design_info = {}
        self.hierarchy = {}
        self.module_declarations = {}
        self.entity_to_class = {}
        self.entity_to_path = {}

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

    def __vcd_file_parser(self, vcd_file_path):
        """Parses vcd file and builds hierarchy of modules"""
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
            signal_match = re.match(REGEX_STRING_MATCH_SIGNAL, line)

            if scope_module_match:
                if skip_level == 0:
                    module_name = scope_module_match.group(1)
                    current_path.append(module_name)

                    current_module = self.hierarchy
                    for path_part in current_path:
                        current_module = current_module.setdefault(path_part, {JSON_OBJ_NAME_SIGNALS: {}})

            elif scope_struct_match or scope_interface_match or scope_union_match:
                skip_level += 1

            if signal_match and skip_level == 0:
                signal_width = int(signal_match.group(1))
                signal_name = signal_match.group(2)

                current_module = self.hierarchy
                for path_part in current_path:
                    current_module = current_module[path_part]
                current_module[JSON_OBJ_NAME_SIGNALS][signal_name] = signal_width

            elif line == STRING_VCD_UNSCOPE:
                if skip_level > 0:
                    skip_level -= 1
                elif current_path:
                    current_path.pop()

    def __process_hierarchy(self, node, current_path="", last_valid_path=""):
        """Processes generated hierarchy tree and builds base for design_info"""
        for key, value in node.items():
            if key == JSON_OBJ_NAME_SIGNALS:
                continue

            full_path = ""

            if self.module_declarations.get(key) is None and self.entity_to_path.get(key) is None:
                full_path = f"{current_path}" if current_path else ""
                
                if last_valid_path:
                    self.design_info[last_valid_path][JSON_OBJ_NAME_SIGNALS].update(value[JSON_OBJ_NAME_SIGNALS])
                
            else:
                full_path = f"{current_path}.{key}" if current_path else key
                self.design_info[full_path] = {
                    JSON_OBJ_NAME_DECLARE_PATH: None,
                    JSON_OBJ_NAME_MODULE_NAME: None,
                    JSON_OBJ_NAME_SIGNALS: value.get(JSON_OBJ_NAME_SIGNALS),
                }
                last_valid_path = full_path

            if isinstance(value, dict):
                self.__process_hierarchy(value, full_path, last_valid_path)

    def parse(self, vcd_file_path, f_list):
        """Parses the VCD file and design files to generate a design hierarchy."""
        if not os.path.isfile(vcd_file_path):
            raise FileNotFoundError(f"The file {vcd_file_path} does not exist.")

        self.__vcd_file_parser(vcd_file_path)

        for line in f_list.splitlines():
            filepath = line.strip()

            if not os.path.isfile(filepath):
                print(f"File {filepath} not found.")
                continue

            try:
                with open(filepath, "r") as f:
                    content = f.read()
                    modules = re.findall(REGEX_STRING_MATCH_VERILOG_MODULE_DECLARE, content, re.MULTILINE)

                    for module in modules:
                        self.module_declarations[module] = filepath

                    entities = re.finditer(REGEX_STRING_MATCH_VERILOG_ENTITY, content, re.MULTILINE | re.DOTALL)

                    for entity in entities:
                        module_class = entity.group(1)
                        module_entity = entity.group(2)

                        self.entity_to_path[module_entity] = filepath
                        self.entity_to_class[module_entity] = module_class

            except Exception as e:
                print(f"Failed to read {filepath}: {e}")

        self.__process_hierarchy(self.hierarchy)

        for path, _ in self.design_info.items():
            module_name = path.split(".")[-1]

            if self.module_declarations.get(module_name) is not None:
                self.design_info[path][JSON_OBJ_NAME_DECLARE_PATH] = self.module_declarations.get(module_name)
                self.design_info[path][JSON_OBJ_NAME_MODULE_NAME] = module_name
                continue

            if self.entity_to_class.get(module_name) is not None:
                module_class = self.entity_to_class.get(module_name)
                if self.module_declarations.get(module_class) is not None:
                    self.design_info[path][JSON_OBJ_NAME_DECLARE_PATH] = self.module_declarations.get(module_class)
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
