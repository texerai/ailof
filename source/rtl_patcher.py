# Copyright (c) 2024 texer.ai. All rights reserved.
import json
import random
import re
import sys

REGEX_STRING_MATCH_SPEC_MODULE_BEGIN = r"module\s+{}(?:\s+import\s+[\w:.*]+;)?(?:\s*#\(\s*([\s\S]*?)\s*\))?\s*\("
REGEX_STRING_MATCH_OUTPUT_SIGNAL = r"\boutput\s+(?:wire|logic|reg)?\s*(?:\[.*?\]\s*)?(?:.*,\s*)*{}\s*(?=[,;])"
REGEX_STRING_MATCH_INPUT_SIGNAL = r"\binput\s+(?:wire|logic|reg)?\s*(?:\[.*?\]\s*)?(?:.*,\s*)*{}\s*(?=[,;])"
REGEX_STRING_MATCH_MODULE_PORTS = r"module\s+{}\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\([^;]*?\);"
REGEX_STRING_MATCH_SIGNAL = r"(?<![\w.]){}\b(?![\w.])"
REGEX_STRING_MATCH_INSTANCE_BEGIN = r"{}\ +(#\([^;]*?\))?\s+\)\ {}\ +\("

BACKUP_FILE = "./backup.json"


def __find_module_declaration(verilog_code):
    """
    A function to find the module declaration in the Verilog code.
    """
    lines = verilog_code.split("\n")
    declaration = []
    in_module = False
    paren_count = 0

    for line in lines:
        line = re.sub(r"//.*$", "", line)

        if not in_module:
            if re.match(r"\s*module\s+\w+", line):
                in_module = True
                declaration.append(line)
                paren_count = line.count("(") - line.count(")")
                if paren_count == 0 and ";" in line:
                    return "\n".join(declaration)
                continue
        else:
            declaration.append(line)
            paren_count += line.count("(") - line.count(")")
            if paren_count == 0 and ";" in line:
                return "\n".join(declaration)


def __is_signal_port(verilog_code, signal_name, port_type):
    """
    A function to check if the signal is a input or output port of the module.
    """
    module_decl = __find_module_declaration(verilog_code)
    
    if not module_decl:
        return False

    lines = [line.strip() for line in module_decl.split("\n")]

    merged_lines = []
    current_line = ""
    for line in lines:
        if not line or line.isspace():
            continue

        line = re.sub(r"//.*$", "", line)
        current_line += " " + line
        if not line.rstrip().endswith(","):
            merged_lines.append(current_line.strip())
            current_line = ""

    for line in merged_lines:
        if not line.startswith(port_type):
            continue

        port_list = re.sub(r"^" + port_type + r"\s+(wire|reg|logic)?\s*", "", line)

        port_list = re.sub(r"\[.*?\]", "", port_list)

        ports = [p.strip() for p in port_list.split(",")]

        if signal_name in ports:
            return True

    return False


def __extract_module_parts(verilog_code, module_name):
    """
    A function to extract the header, definition and body of the module from the Verilog code.
    """
    module_pattern = f"module\\s+{module_name}\\s*"
    module_match = re.search(module_pattern, verilog_code)
    if not module_match:
        return None, None, None

    header_content = verilog_code[: module_match.start()].strip()

    start_pos = module_match.start()
    pos = module_match.end()

    paren_count = 0
    port_start = None
    port_end = None

    while pos < len(verilog_code):
        char = verilog_code[pos]
        if char == "(":
            if paren_count == 0:
                port_start = pos
            paren_count += 1
        elif char == ")":
            paren_count -= 1
            if paren_count == 0:
                port_end = pos + 1
                break
        pos += 1

    if port_start is None or port_end is None:
        return None, None, None

    # Find the semicolon after port list
    pos = port_end
    while pos < len(verilog_code) and verilog_code[pos] != ";":
        pos += 1
    if pos >= len(verilog_code):
        return None, None, None

    module_definition = verilog_code[start_pos : pos + 1]

    # Find module body (everything between module definition and matching endmodule)
    body_start = pos + 1
    pos = body_start

    while pos < len(verilog_code):
        # Look for "endmodule" keyword
        if verilog_code[pos:].lstrip().startswith("endmodule"):
            # Extract body excluding the endmodule keyword
            module_body = verilog_code[body_start:pos].strip()
            return header_content, module_definition, module_body
        pos += 1

    return None, None, None


def __replace_internal_signal(signal_name, module_body):
    """
    A function to replace the internal signal with the modified signal.
    """
    lines = module_body.split("\n")

    for i, line in enumerate(lines):
        if not line.strip():
            continue

        eq_pos = line.find("=")
        le_pos = line.find("<=")

        if eq_pos == -1 and le_pos == -1:
            continue

        op_pos = le_pos if le_pos != -1 else eq_pos

        left_part = line[:op_pos].strip()
        right_part = line[op_pos:].strip()

        modified_right_part = re.sub(rf"\b{signal_name}\b", f"modified_{signal_name}", right_part)

        if right_part != modified_right_part:
            lines[i] = f"{left_part} {modified_right_part}"

    return "\n".join(lines)


def insert_gate(design_file_path, module_name, signal_name, internal_signal_name):
    """
    A function to insert a AND gate logic for particular signal into the Verilog code.
    """
    verilog_code = ""

    with open(design_file_path, "r") as infile:
        verilog_code = "".join(infile.readlines())

    # Check if the signal is a output or input port of the module.
    is_output_port = __is_signal_port(verilog_code, signal_name, "output")
    is_input_port = __is_signal_port(verilog_code, signal_name, "input")

    header_content, module_definition, module_body = __extract_module_parts(verilog_code, module_name)

    if module_definition is None:
        err_message = f"Error: Module '{module_name}' not found in the Verilog code."
        return False, err_message

    # Check if the signal is used in the module.
    if not re.search(REGEX_STRING_MATCH_SIGNAL.format(signal_name), module_body):
        err_message = f"Warning: Signal '{signal_name}' not found in module '{module_name}'."
        return False, err_message

    modified_signal_name = f"modified_{signal_name}"

    # Insert the gate logic into the Verilog code.
    if is_output_port:
        gate_logic = f"    assign {signal_name} = {modified_signal_name} & {internal_signal_name};\n"
        modified_body = re.sub(rf"(?<!\w){signal_name}(?!\w)", modified_signal_name, module_body)
    else:
        gate_logic = f"    wire {modified_signal_name};\n"
        gate_logic += f"    assign {modified_signal_name} = {signal_name} & {internal_signal_name};\n"

        if is_input_port:
            modified_body = re.sub(rf"(?<!\w){signal_name}(?!\w)", modified_signal_name, module_body)
        else:
            modified_body = __replace_internal_signal(signal_name, module_body)

    modified_body = gate_logic + modified_body
    modified_code = f"{header_content}\n\n{module_definition}\n{modified_body}\nendmodule"

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


class RtlPatcher:
    def __init__(self, json_design_hierarchy, selected_modules, signals_to_punch):
        sys.stdout.write("\x1b[2J\x1b[H")
        print(f"RTL patcher is initialized with {len(signals_to_punch)} signals to process.\n")
        self.json_design_hierarchy = json_design_hierarchy
        self.selected_modules = selected_modules
        self.signals_to_punch = signals_to_punch
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
            import_function = f'import "DPI-C" function void fuzz_{top_instance}('
            for signal in data["signals"]:
                import_function += f"output {signal}, "
            import_function = import_function[:-2] + ");"

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
                    outfile.write(f"{import_function}\n\n{verilog_code}")
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
