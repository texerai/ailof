# Copyright (c) 2024 texer.ai. All rights reserved.
import json
import random
import re
import sys

REGEX_STRING_MATCH_MODULE_BEGIN = r"(?i)\bmodule\s+(\w+)\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\(([^;]*?)\)\s*;"
REGEX_STRING_MATCH_SPEC_MODULE_BEGIN = r"module\s+{}(?:\s+import\s+[\w:.*]+;)?(?:\s*#\(\s*([\s\S]*?)\s*\))?\s*\("
REGEX_STRING_MATCH_OUTPUT_SIGNAL = r"output(?:\s+(?:wire|logic|reg))?\s+(?:\[.*?\]\s+)?{}\b"
REGEX_STRING_MATCH_FULL_MODULE = r"module\s+{}\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\([^;]*?\);\s*(.*?)\s*endmodule"
REGEX_STRING_MATCH_MODULE_PORTS = r"module\s+{}\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\([^;]*?\);"
REGEX_STRING_MATCH_SIGNAL = r"\b{}\b"
REGEX_STRING_MATCH_INSTANCE_BEGIN = r"{}\ +(#\([^;]*?\))?\s+\)\ {}\ +\("
REGEX_STRING_MATCH_IMPORT_FUNCTION = r'import "DPI-C" function void (\w+)\s*\(([^)]*)\);'

BACKUP_FILE = "./backup.json"


def is_signal_output(verilog_code, module_name, signal_name):
    match = re.search(REGEX_STRING_MATCH_MODULE_BEGIN, verilog_code, re.DOTALL)
    if not match:
        err_message = f"Error: Module not found {module_name}"
        return False, err_message

    module_declaration = match.group(0)
    if re.search(REGEX_STRING_MATCH_OUTPUT_SIGNAL.format(signal_name), module_declaration) is None:
        err_message = f"Error: Signal {signal_name} not found."
        return False, err_message

    return True, ""


def insert_gate(design_file_path, module_name, signal_name, internal_signal_name):
    verilog_code = ""
    with open(design_file_path, "r") as infile:
        verilog_code = "".join(infile.readlines())

    is_output_port = is_signal_output(verilog_code, module_name, signal_name)

    match = re.search(REGEX_STRING_MATCH_FULL_MODULE.format(module_name), verilog_code, re.DOTALL)
    if not match:
        err_message = f"Module '{module_name}' not found in the Verilog code."
        return False, err_message

    module_body = match.group(1)

    match = re.search(REGEX_STRING_MATCH_MODULE_PORTS.format(module_name), verilog_code, re.DOTALL)
    module_definition = match.group(0)

    # Check if the signal exists in the module
    # It is quite possible that the signal in the port is never used
    # in the implementation. So just output the warning.
    if not re.search(REGEX_STRING_MATCH_SIGNAL.format(signal_name), module_body):
        err_message = f"Warning: Signal '{signal_name}' not found in module '{module_name}'."
        return False, err_message

    # Modify the signal to include the gate.
    if is_output_port:
        gate_logic = f"    assign {signal_name} = modified_{signal_name} & {internal_signal_name};\n"
    else:
        gate_logic = f"    wire modified_{signal_name};\n"
        gate_logic += f"    assign modified_{signal_name} = {signal_name} & {internal_signal_name};\n"

    modified_body = re.sub(rf"(?<!\w){signal_name}(?!\w)", rf"modified_{signal_name}", module_body)
    modified_body = gate_logic + modified_body
    modified_code = f"{module_definition}\n{modified_body}\nendmodule"

    with open(design_file_path, "w") as out_file:
        out_file.write(modified_code)

    return True, ""


def add_port_to_instance(file_path, module_name, instance_name, new_port):
    with open(file_path, "r") as file:
        verilog_code = "".join(file.readlines())

    m = re.search(REGEX_STRING_MATCH_INSTANCE_BEGIN.format(module_name, instance_name), verilog_code)
    if m:
        before = verilog_code[: m.start()]
        found_pattern = m.group(0)
        after = verilog_code[m.end() :]
    else:
        err_message = f"Error: Module '{module_name}' with instance name {instance_name} not found in the Verilog code."
        return False, err_message

    modified_code = before + found_pattern
    modified_code += f"\n.{new_port}({new_port}),"
    modified_code += after

    with open(file_path, "w") as out_file:
        out_file.write(modified_code)

    return True, ""


def add_port_to_module(file_path, module_name, new_port):
    with open(file_path, "r") as file:
        verilog_code = "".join(file.readlines())

    m = re.search(REGEX_STRING_MATCH_SPEC_MODULE_BEGIN.format(module_name), verilog_code)
    if m:
        before = verilog_code[: m.start()]
        found_pattern = m.group(0)
        after = verilog_code[m.end() :]
    else:
        err_message = f"Module '{module_name}' not found in the Verilog code."
        return False, err_message
    modified_code = before + found_pattern
    modified_code += f"\ninput {new_port},"
    modified_code += after

    with open(file_path, "w") as out_file:
        out_file.write(modified_code)

    return True, ""


def generate_dpi_always_block(control_signals, import_function):
    match = re.search(REGEX_STRING_MATCH_IMPORT_FUNCTION, import_function)
    func_name = match.group(1)
    params = match.group(2)

    param_list = [param.strip() for param in params.split(",")]
    cleaned_params = [param.replace("output ", "", 1).strip() for param in param_list]
    new_params = ", ".join(cleaned_params)

    clock = control_signals["clock"]
    edge = control_signals["edge"]

    dpi_always_block = f"""
    always_ff @({edge} {clock}) begin
        {func_name}({new_params});
    end"""

    return dpi_always_block


def add_dpi_calls(verilog_code, initial_block, always_block):
    parts = verilog_code.rsplit("endmodule", 1)
    if len(parts) == 2:
        modified_code = parts[0] + "\n" + initial_block + always_block + "\nendmodule" + parts[1]
        return modified_code
    else:
        return verilog_code


class RtlPatcher:
    def __init__(self, json_design_hierarchy, selected_modules, signals_to_punch):
        self.json_design_hierarchy = json_design_hierarchy
        self.selected_modules = selected_modules["selected_modules"]
        self.signals_to_punch = signals_to_punch["selected_signals"]
        self.control_signals = signals_to_punch["control_signals"]
        sys.stdout.write("\x1b[2J\x1b[H")
        print(f"RTL patcher is initialized with {len(self.signals_to_punch)} signal(s) to process.\n")
        id = 0
        for signal_hierarchy, signal in self.signals_to_punch.items():
            signal["punch_name"] = f"punch_out_{signal['name']}_{id}"
            id += 1

    def insert_gates(self, design_file_path, hierarchy, module_name):
        for signal_hierarchy, signal in self.signals_to_punch.items():
            signal_name = signal["name"]
            gate_input_signal = signal["punch_name"]

            is_inserted, err_message = insert_gate(design_file_path, module_name, signal_name, gate_input_signal)

            if len(err_message) > 0:
                print(err_message)

        return True, ""

    def punch_through_instances(self, hierarchy):
        for signal_hierarchy, signal in self.signals_to_punch.items():
            gate_input_name = signal["punch_name"]
            curr_hierarchy = ""
            instances = hierarchy.split(".")
            first_instance = instances[0]
            seperator = f"{first_instance}."
            previous_file_path = self.json_design_hierarchy[first_instance]["declaration_path"]
            for instance in instances[1:]:
                curr_hierarchy += seperator + instance
                curr_module_name = self.json_design_hierarchy[curr_hierarchy]["module_name"]
                is_added, err_message = add_port_to_instance(previous_file_path, curr_module_name, instance, gate_input_name)
                if not is_added:
                    return False, err_message
                previous_file_path = self.json_design_hierarchy[curr_hierarchy]["declaration_path"]
                seperator = "."

        return True, ""

    def punch_through_modules(self, hierarchy):
        for signal_hierarchy, signal in self.signals_to_punch.items():
            gate_input_name = signal["punch_name"]
            instances = hierarchy.split(".")
            first_instance = instances[0]
            seperator = f"{first_instance}."
            curr_hierarchy = ""
            for instance in instances[1:]:
                curr_hierarchy += seperator + instance
                file_path = self.json_design_hierarchy[curr_hierarchy]["declaration_path"]
                module_name = self.json_design_hierarchy[curr_hierarchy]["module_name"]
                is_added, err_message = add_port_to_module(file_path, module_name, gate_input_name)
                if not is_added:
                    return False, err_message
                seperator = "."

        return True, ""

    def create_dpi(self):
        top_instances = {}
        for signal_hierarchy, signal in self.signals_to_punch.items():
            gate_input_name = signal["punch_name"]
            instances = signal_hierarchy.split(".")
            top_instance = instances[0]
            if top_instance not in top_instances:
                top_instances[top_instance] = {}
                top_instances[top_instance]["declaration_path"] = self.json_design_hierarchy[top_instance]["declaration_path"]
                top_instances[top_instance]["signals"] = [gate_input_name]
            else:
                top_instances[top_instance]["signals"].append(gate_input_name)

        for top_instance, data in top_instances.items():
            import_init_function = 'import "DPI-C" function void init();'
            import_fuzz_function = f'import "DPI-C" function void fuzz_{top_instance}('
            for signal in data["signals"]:
                import_fuzz_function += f"output {signal}, "
            import_fuzz_function = import_fuzz_function[:-2] + ");"

            initial_block = "    initial begin\n"
            initial_block += "        init();\n"
            initial_block += "    end\n"
            always_block = generate_dpi_always_block(self.control_signals, import_fuzz_function)

            cpp_function = '#include "logic_fuzzer.h"\n\n'
            cpp_function += "#include <memory>\n"
            cpp_function += "#include <vector>\n"
            cpp_function += "#include <cstdint>\n\n"
            cpp_function += "static std::vector<std::shared_ptr<lf::LogicFuzzer>> fuzzers;\n\n"
            cpp_function += 'extern "C" void init()\n{\n'
            cpp_function += f"    const int kSeed = {random.randint(0, 1000)};\n"
            cpp_function += f"    for (size_t i = 0; i < {len(top_instances)}; ++i)\n"
            cpp_function += "    {\n"
            cpp_function += "        fuzzers.push_back(std::make_shared<lf::LogicFuzzer>(i + kSeed));\n"
            cpp_function += "    }\n"
            cpp_function += "}\n\n"

            cpp_function += f'extern "C" void fuzz_{top_instance}('
            for signal in data["signals"]:
                cpp_function += f"int* {signal}, "
            cpp_function = cpp_function[:-2] + ")\n{\n"
            i = 0
            for signal in data["signals"]:
                cpp_function += f"    *{signal} = fuzzers[{i}]->Congest();\n"
            cpp_function += "}"

            verilog_code = ""
            try:
                with open(data["declaration_path"], "r") as infile:
                    verilog_code = "".join(infile.readlines())
                with open(data["declaration_path"], "w") as outfile:
                    modified_code = add_dpi_calls(verilog_code, initial_block, always_block)
                    outfile.write(f"{import_init_function}\n{import_fuzz_function}\n\n{modified_code}")
                with open(f"{top_instance}_dpi.cpp", "w") as outfile:
                    outfile.write(cpp_function)
            except Exception as e:
                err_message = f"Error: {e}"
                return False, err_message

        return True, ""

    def patch(self):
        # Backup files.
        try:
            backed_up_files = {}
            for hierarchy, data in self.selected_modules.items():
                instances = hierarchy.split(".")
                curr_hierarchy = ""
                seperator = ""
                for instance in instances:
                    curr_hierarchy += seperator + instance
                    file_path = self.json_design_hierarchy[curr_hierarchy]["declaration_path"]
                    verilog_code = ""
                    with open(file_path, "r") as infile:
                        verilog_code = "".join(infile.readlines())
                    backed_up_files[file_path] = verilog_code
                    seperator = "."
            with open(BACKUP_FILE, "w") as json_file:
                json.dump(backed_up_files, json_file, indent=4)
        except Exception as e:
            err_message = f"Error: {e}"
            return False, err_message

        # Filter only modules that were selected.
        # FIXME: Should be refactored. Traverse only signals.
        selected_signal_modules = {}
        for signal_hierarchy, signal_data in self.signals_to_punch.items():
            module_hierarchy = ".".join(signal_hierarchy.split(".")[:-1])
            if module_hierarchy not in selected_signal_modules:
                if module_hierarchy in self.selected_modules:
                    selected_signal_modules[module_hierarchy] = self.selected_modules[module_hierarchy]
                else:
                    print(f"Warning: {module_hierarchy} in not in selected modules.")

        # Patch.
        for hierarchy, data in selected_signal_modules.items():
            module_name = self.json_design_hierarchy[hierarchy]["module_name"]

            # Insert gates.
            is_inserted, err_message = self.insert_gates(data["declaration_path"], hierarchy, module_name)

            if is_inserted:
                # Punch through instances.
                is_punched, err_message = self.punch_through_instances(hierarchy)

                if is_punched:
                    # Punch through modules.
                    is_punched, err_message = self.punch_through_modules(hierarchy)

                    if is_punched:
                        # Create DPI.
                        is_created, err_message = self.create_dpi()
                        if not is_created:
                            return False, err_message
                    else:
                        return False, err_message
                else:
                    return False, err_message
            else:
                return False, err_message

        return True, ""
