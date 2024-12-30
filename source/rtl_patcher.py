# Copyright (c) 2024 texer.ai. All rights reserved.
import re

def is_signal_output(verilog_code, module_name, signal_name):
    # Regex pattern to find the specific module
    module_pattern = r"(?i)\bmodule\s+(\w+)\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\(([^;]*?)\)\s*;"
    match = re.search(module_pattern, verilog_code, re.DOTALL)

    if not match:
        print(f"module not found {module_name}")
        return False  # Module not found

    # Extract the module's port list
    module_declaration = match.group(0)

    # Regex pattern to find inputs within the module
    input_pattern = rf"output(?:\s+(?:wire|logic|reg))?\s+(?:\[.*?\]\s+)?{signal_name}\b"
    return re.search(input_pattern, module_declaration) is not None

def insert_gate(verilog_code, module_name, signal_name, internal_signal_name):
    is_output_port = is_signal_output(verilog_code, module_name, signal_name)

    # Regex to find the module declaration and implementation
    module_pattern = rf"module\s+{module_name}\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\([^;]*?\);\s*(.*?)\s*endmodule"
    match = re.search(module_pattern, verilog_code, re.DOTALL)
    if not match:
        raise ValueError(f"Module '{module_name}' not found in the Verilog code.")
    module_body = match.group(1)

    # Regex to find only decleration.
    module_definition_pattern = rf"module\s+{module_name}\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\([^;]*?\);"
    match = re.search(module_definition_pattern, verilog_code, re.DOTALL)
    module_definition = match.group(0)

    # Check if the signal exists in the module
    # It is quite possible that the signal in the port is never used
    # in the implmentation. So just output the warning.
    signal_pattern = rf"\b{signal_name}\b"
    if not re.search(signal_pattern, module_body):
        print(f"Warnign: Signal '{signal_name}' not found in module '{module_name}'.")
        return False, ""

    # Modify the signal to include the gate.
    if is_output_port:
        gate_logic = f"    assign {signal_name} = modified_{signal_name} & {internal_signal_name};\n"
    else:
        gate_logic = f"    wire modified_{signal_name};\n"
        gate_logic += f"    assign modified_{signal_name} = {signal_name} & {internal_signal_name};\n"

    # Replace occurrences of the signal in assignments/logic with the modified signal
    modified_body = re.sub(
        rf"(?<!\w){signal_name}(?!\w)",
        rf"modified_{signal_name}",
        module_body
    )

    # Add the AND gate logic at the start of the module body
    modified_body = gate_logic + modified_body

    # Replace the original module implementation with the modified implementation
    modified_code = f"{module_definition}\n{modified_body}\nendmodule"

    return True, modified_code

def add_port_to_instance(file_path, module_name, instance_name, new_port):
    print("Adding port to instance:")
    print(f"  {file_path}")
    print(f"  {module_name}")
    print(f"  {instance_name}")
    print(f"  {new_port}")
    with open(file_path, 'r') as file:
        verilog_code = "".join(file.readlines())

    module_start_pattern = rf"{module_name}\ +(#\([^;]*?\))?\s+\)\ {instance_name}\ +\("
    m = re.search(module_start_pattern, verilog_code)
    if m:
        before = verilog_code[:m.start()]
        found_pattern = m.group(0)
        after = verilog_code[m.end():]
    else:
        raise ValueError(f"Module '{module_name}' with instance name {instance_name} not found in the Verilog code.")
    modified_code = before + found_pattern
    modified_code += f"\n.{new_port}({new_port}),"
    modified_code += after

    with open(file_path, "w") as out_file:
        out_file.write(modified_code)

    return modified_code

def add_port_to_module(file_path, module_name, new_port):
    print(f"Adding module port at {file_path}")
    with open(file_path, 'r') as file:
        verilog_code = "".join(file.readlines())

    module_start_pattern = rf"module\s+{module_name}(?:\s+import\s+[\w:.*]+;)?(?:\s*#\(\s*([\s\S]*?)\s*\))?\s*\("
    m = re.search(module_start_pattern, verilog_code)
    if m:
        before = verilog_code[:m.start()]
        found_pattern = m.group(0)
        after = verilog_code[m.end():]
    else:
        raise ValueError(f"Module '{module_name}' not found in the Verilog code.")
    modified_code = before + found_pattern
    modified_code += f"\ninput {new_port},"
    modified_code += after

    with open(file_path, "w") as out_file:
        out_file.write(modified_code)

    return modified_code

class RtlPatcher:
    def __init__(self, json_design_hierarchy, selected_modules, signals_to_punch):
        self.json_design_hierarchy = json_design_hierarchy
        self.selected_modules = selected_modules
        self.signals_to_punch = signals_to_punch

    def insert_gates(self, design_file_path, hierarchy, module_name):
        for signal in self.signals_to_punch[hierarchy]:
            signal_name = signal["name"]
            gate_input_signal = f"punch_out_{signal_name}"

            verilog_code = ""
            with open(design_file_path, "r") as design_file:
                for line in design_file:
                    verilog_code += line

            is_patched, patched_verilog = insert_gate(verilog_code, module_name, signal_name, gate_input_signal)

            if is_patched:
                with open(design_file_path, "w") as out_file:
                    out_file.write(patched_verilog)

    def punch_through_instances(self, hierarchy):
        for signal in self.signals_to_punch[hierarchy]:
            gate_input_name = f"punch_out_{signal['name']}"
            # Punch out the inputs of the gates.
            curr_hierarchy = ""
            instances = hierarchy.split(".")
            first_instance = instances[0]
            seperator = f"{first_instance}."
            previous_file_path = self.json_design_hierarchy[first_instance]["declaration_path"]
            # ex_stage_i.fpu_i.i_fpnew_bulk.i_opgroup_block
            for instance in instances[1:]:
                curr_hierarchy += seperator + instance
                curr_module_name = self.json_design_hierarchy[curr_hierarchy]["module_name"]
                add_port_to_instance(previous_file_path, curr_module_name, instance, gate_input_name)
                previous_file_path = self.json_design_hierarchy[curr_hierarchy]["declaration_path"]
                seperator = "."

    def punch_through_modules(self, hierarchy):
        for signal in self.signals_to_punch[hierarchy]:
            gate_input_name = f"punch_out_{signal['name']}"
            instances = hierarchy.split(".")
            first_instance = instances[0]
            seperator = f"{first_instance}."
            curr_hierarchy = ""
            for instance in instances[1:]:
                curr_hierarchy += seperator + instance
                file_path = self.json_design_hierarchy[curr_hierarchy]["declaration_path"]
                module_name = self.json_design_hierarchy[curr_hierarchy]["module_name"]
                add_port_to_module(file_path, module_name, gate_input_name)
                seperator = "."

    def patch(self):
        for hierarchy, data in self.selected_modules.items():
            module_name = self.json_design_hierarchy[hierarchy]["module_name"]

            # Insert gates.
            self.insert_gates(data["declaration_path"], hierarchy, module_name)

            # Punch through instances.
            self.punch_through_instances(hierarchy)

            self.punch_through_modules(hierarchy)

