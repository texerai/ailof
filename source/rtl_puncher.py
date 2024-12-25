# Copyright (c) 2024 texer.ai. All rights reserved.
import re

def is_signal_input(verilog_code, module_name, signal_name):
    # Regex pattern to find the specific module
    module_pattern = r"(?i)\bmodule\s+(\w+)\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\(([^;]*?)\)\s*;"
    match = re.search(module_pattern, verilog_code, re.DOTALL)

    if not match:
        print(f"module not found {module_name}")
        return False  # Module not found

    # Extract the module's port list
    module_declaration = match.group(0)

    # Regex pattern to find inputs within the module
    input_pattern = rf"input(?:\s+(?:wire|logic|reg))?\s+(?:\[.*?\]\s+)?{signal_name}\b"
    return re.search(input_pattern, module_declaration) is not None

def modify_verilog_module(verilog_code, module_name, signal_name, internal_signal_name):
    # Regex to find the module declaration and implementation
    module_pattern = rf"module\s+{module_name}\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\([^;]*?\);\s*(.*?)\s*endmodule"
    match = re.search(module_pattern, verilog_code, re.DOTALL)

    if not match:
        raise ValueError(f"Module '{module_name}' not found in the Verilog code.")

    # Extract the module body (code between ");" and "endmodule")
    module_body = match.group(1)

    # Check if the signal exists in the module
    signal_pattern = rf"\b{signal_name}\b"
    if not re.search(signal_pattern, module_body):
        raise ValueError(f"Signal '{signal_name}' not found in module '{module_name}'.")
    # Modify the signal to include an AND gate
    # Create a wire for the modified signal
    and_gate_logic = f"    wire modified_{signal_name};\n"
    and_gate_logic += f"    assign modified_{signal_name} = {signal_name} & {internal_signal_name};\n"

    # Replace occurrences of the signal in assignments/logic with the modified signal
    modified_body = re.sub(
        rf"(?<!\w){signal_name}(?!\w)",
        rf"modified_{signal_name}",
        module_body
    )

    # Add the AND gate logic at the start of the module body
    modified_body = and_gate_logic + modified_body

    # Updated regex to match only the module definition
    module_definition_pattern = rf"module\s+{module_name}\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\([^;]*?\);"
    match = re.search(module_definition_pattern, verilog_code, re.DOTALL)
    module_definition = ""
    if match:
        module_definition = match.group(0)
    else:
        print(f"Module '{module_name}' definition not found.")

    # Replace the original module implementation with the modified implementation
    modified_code = f"{module_definition}\n{modified_body}\nendmodule"

    return modified_code

def insert_gate(verilog_code, module_name, signal_name, gate_second_input_name):
    if is_signal_input(verilog_code, module_name, signal_name):
        return modify_verilog_module(verilog_code, module_name, signal_name, gate_second_input_name))

class RtlPuncher:
    def __init__(self, json_design_hierarchy, selected_modules, signals_to_punch):
        self.json_design_hierarchy = json_design_hierarchy
        self.selected_modules = selected_modules
        self.signals_to_punch = signals_to_punch

    def patch_verilog(self, design_file_path, signal_name, gate_output_signal, gate_input_signal):
        verilog_code = ""
        with open(design_file_path, "r") as design_file:
            for line in design_file:
                verilog_code += line

        patched_verilog = insert_gate(verilog_code, signal_name, gate_output_signal, gate_input_signal)

        with open(design_file_path, "w") as design_file:
            design_file.write(patched_verilog)

    def punch(self):
        for module, data in self.selected_modules.items():
            instances = module.split(".")
            design_files = {}
            seperator = ""
            hierarchy = ""
            print("Signals:")
            i = 0
            for signal in self.signals_to_punch[module]:
                print(f"    {signal['name']} | {signal['certainty']}")
                gate_output = f"{signal['name']}_prime"
                gate_input = f"punch_signal_{i}"
                self.patch_verilog(data["declaration_path"], signal["name"], gate_output, gate_input)
                i += 1

            for instance in instances:
                hierarchy += seperator + instance
                module_declaration_path = self.json_design_hierarchy[hierarchy]["declaration_path"]
                module_name = self.json_design_hierarchy[hierarchy]["module_name"]
                design_files[hierarchy] = module_declaration_path
                seperator = "."
                print(f"{hierarchy}\n    {module_declaration_path}\n    {module_name}")

def test():
    verilog_code = ""
    module_name = "serdiv"
    file_name = "/home/kabylkas/cva6/core/serdiv.sv"
    signal_name = "out_rdy_i"
    with open(file_name, "r") as design_file:
        for line in design_file:
            verilog_code += line
    if is_signal_input(verilog_code, module_name, signal_name):
        print(modify_verilog_module(verilog_code, module_name, signal_name, "x"))
test()