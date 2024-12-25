# Copyright (c) 2024 texer.ai. All rights reserved.
import re

# Auxiliary functions.
def handle_signal_in_code(verilog_code, signal_name, new_and_signal_name, and_input_signal):
    """
    Handles signals in continuous assignments and procedural blocks.
    """
    # Exclude commented lines
    lines = verilog_code.splitlines()
    modified_lines = []

    for line in lines:
        # Skip comments
        if "//" in line:
            modified_lines.append(line)
            continue

        # Match and replace procedural assignments
        if f"{signal_name} <=" in line:
            pattern = rf"({signal_name}\s*<=\s*)(.*?);"
            line = re.sub(
                pattern,
                rf"\1{new_and_signal_name} <= \2 & {and_input_signal};",
                line,
            )

        modified_lines.append(line)

    # Join the lines back into a single string
    return "\n".join(modified_lines)

def break_input_port_with_and(verilog_code, port_name, intermediate_signal_name, and_input_signal):
    """
    Breaks an input port and inserts an AND gate with a new intermediate signal.

    Parameters:
        verilog_code (str): The original Verilog code as a string.
        port_name (str): The name of the input port to break.
        intermediate_signal_name (str): The intermediate signal replacing the input.
        and_input_signal (str): The second input to the AND gate.

    Returns:
        str: Modified Verilog code with the AND gate inserted.
    """
    intermediate_declaration = f"    wire {intermediate_signal_name};\n"
    and_assignment = f"    assign {intermediate_signal_name} = {port_name} & {and_input_signal};\n"

    # Add intermediate declaration and AND gate
    module_header_pattern = r"(module\s+\w+\s*\(.*?\);\s*\n)"
    modified_code = re.sub(module_header_pattern, r"\1" + intermediate_declaration, verilog_code, count=1)

    # Replace all occurrences of the input signal with the intermediate signal
    modified_code = re.sub(rf"\b{port_name}\b", intermediate_signal_name, modified_code)

    # Insert the AND assignment after the module header
    modified_code = re.sub(module_header_pattern, r"\1" + and_assignment, modified_code, count=1)

    return modified_code

def break_output_port_with_and(verilog_code, output_name, intermediate_signal_name, and_input_signal):
    """
    Breaks an output port and inserts an AND gate with a new intermediate signal.

    Parameters:
        verilog_code (str): The original Verilog code as a string.
        output_name (str): The name of the output signal to break.
        intermediate_signal_name (str): The intermediate signal replacing the output.
        and_input_signal (str): The second input to the AND gate.

    Returns:
        str: Modified Verilog code with the AND gate inserted.
    """
    # Step 1: Replace all procedural assignments to the output signal with the intermediate signal
    procedural_pattern = rf"(?<!//.*)(?<!\w)({output_name}\s*<=\s*)(.*?);"
    def replace_procedural(match):
        original_assignment = match.group(2)
        return f"{intermediate_signal_name} <= {original_assignment};"

    modified_code = re.sub(procedural_pattern, replace_procedural, verilog_code)

    # Step 2: Add the intermediate signal declaration
    reg_declaration = f"    reg {intermediate_signal_name};\n"
    module_header_pattern = r"(module\s+\w+\s*\(.*?\);\s*\n)"
    modified_code = re.sub(module_header_pattern, r"\1" + reg_declaration, modified_code, count=1)

    # Step 3: Add the AND gate assignment for the output signal
    and_assignment = f"    assign {output_name} = {intermediate_signal_name} & {and_input_signal};\n"
    always_block_pattern = r"(always\s*@\(.*?\)\s*begin)"
    modified_code = re.sub(always_block_pattern, and_assignment + r"\n\1", modified_code, count=1)

    return modified_code

class RtlPuncher:
    def __init__(self, json_design_hierarchy, selected_modules, signals_to_punch):
        self.json_design_hierarchy = json_design_hierarchy
        self.selected_modules = selected_modules
        self.signals_to_punch = signals_to_punch

    def insert_gate(self, verilog_code, signal_name, new_and_signal_name, and_input_signal):
        # Check if the signal is an output port
        output_port_pattern = rf"output(?:\s+reg)?\s+{signal_name}\b"
        if re.search(output_port_pattern, verilog_code):
            return break_output_port_with_and(verilog_code, signal_name, new_and_signal_name, and_input_signal)

        # Check if the signal is an input port
        input_port_pattern = rf"input\s+{signal_name}\b"
        if re.search(input_port_pattern, verilog_code):
            return break_input_port_with_and(verilog_code, signal_name, new_and_signal_name, and_input_signal)

        # Handle other cases (assignments and procedural blocks)
        return handle_signal_in_code(verilog_code, signal_name, new_and_signal_name, and_input_signal)

    def patch_verilog(self, design_file_path, signal_name, gate_output_signal, gate_input_signal):
        verilog_code = ""
        with open(design_file_path, "r") as design_file:
            for line in design_file:
                verilog_code += line

        patched_verilog = self.insert_gate(verilog_code, signal_name, gate_output_signal, gate_input_signal)

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