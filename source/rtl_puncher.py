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
    return match.group(1)

def insert_and_gate(verilog_code, target_signal, internal_signal):
    # Add internal signal declaration
    internal_decl = f"    logic {internal_signal};\n"
    verilog_code = re.sub(r"(module\s+\w+\s*\(.*?\);\s*)", rf"\1{internal_decl}", verilog_code, flags=re.DOTALL)

    # Find the target input declaration and insert the AND gate
    and_gate_logic = f"    wire modified_{target_signal};\n"
    and_gate_logic += f"    assign modified_{target_signal} = {target_signal} & {internal_signal};\n"

    verilog_code = re.sub(
        rf"(input\s+.*?\b{target_signal}\b.*?;)",
        rf"\1\n{and_gate_logic}",
        verilog_code
    )

    # Replace occurrences of the target signal in downstream logic
    verilog_code = re.sub(rf"\b{target_signal}\b", rf"modified_{target_signal}", verilog_code)

    return verilog_code


class RtlPuncher:
    def __init__(self, json_design_hierarchy, selected_modules, signals_to_punch):
        self.json_design_hierarchy = json_design_hierarchy
        self.selected_modules = selected_modules
        self.signals_to_punch = signals_to_punch

    def insert_gate(self, verilog_code, module_name, signal_name, new_and_signal_name, and_input_signal):
        pass

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

def test():
    verilog_code = ""
    module_name = "serdiv"
    file_name = "/home/kabylkas/cva6/core/serdiv.sv"
    signal_name = "flush_i"
    with open(file_name, "r") as design_file:
        for line in design_file:
            verilog_code += line
    if is_signal_input(verilog_code, module_name, signal_name):
        print(modify_verilog_module(verilog_code, module_name, "internal", "x"))
test()