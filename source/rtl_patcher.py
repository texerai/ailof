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

        modified_right_part = re.sub(rf"\b{signal}\b", f"modified_{signal}", right_part)

        if right_part != modified_right_part:
            lines[i] = f"{left_part} {modified_right_part}"

    return "\n".join(lines)


def insert_gate(design_file_path, module_name, signal_name, internal_signal_name):
    """
    A function to insert a AND gate logic for particular signal into the Verilog code.
    """
    verilog_code = ""

    param_list = [param.strip() for param in params.split(",")]
    cleaned_params = [param.replace("output ", "", 1).strip() for param in param_list]
    new_params = ", ".join(cleaned_params)

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
    def __init__(self, selected_modules, selected_signals):
        self.selected_modules = selected_modules
        self.selected_signals = selected_signals
        self.grouped_signals = {}
        # Clear the screen and print the header.
        sys.stdout.write("\x1b[2J\x1b[H")
        print(f"RTL patcher is initialized with {len(self.selected_signals)} signal(s) to process.\n")
        # Create unique modification names for each signal.
        id = 0
        for _, signal_data in self.selected_signals.items():
            signal_name = signal_data["name"]
            signal_data["punch_name"] = f"punch_out_{signal_name}_{id}"
            id += 1

    def __preprocess(self):
        # Group signals by parent module.
        for _, signal_data in self.selected_signals.items():
            parent_module_path = signal_data["declaration_path"]
            if parent_module_path not in self.grouped_signals:
                self.grouped_signals[parent_module_path] = []
            self.grouped_signals[parent_module_path].append(signal_data)

    def __backup(self):
        # Create backups of all files that will be modified.
        backed_up_files = {}

        for parent_module_path, _ in self.grouped_signals.items():
            with open(parent_module_path, "r") as f:
                verilog_code = f.read()
            backed_up_files[parent_module_path] = verilog_code

        with open(BACKUP_FILE, "w") as json_file:
            json.dump(backed_up_files, json_file, indent=4)

    def __create_dpi(self, module_name, punch_signals):
        cpp_content = '#include "logic_fuzzer.h"\n\n'
        cpp_content += "#include <memory>\n"
        cpp_content += "#include <vector>\n"
        cpp_content += "#include <cstdint>\n\n"
        cpp_content += "static std::vector<std::shared_ptr<lf::LogicFuzzer>> fuzzers;\n\n"
        cpp_content += f'extern "C" void init_{module_name}()\n{{\n'
        cpp_content += f"    const int kSeed = {random.randint(0, 1000)};\n"
        cpp_content += f"    for (size_t i = 0; i < {1}; ++i)\n"  # TODO: Change this to the number of fuzzers.
        cpp_content += "    {\n"
        cpp_content += "        fuzzers.push_back(std::make_shared<lf::LogicFuzzer>(i + kSeed));\n"
        cpp_content += "    }\n"
        cpp_content += "}\n\n"

        cpp_content += f'extern "C" void fuzz_{module_name}('
        for signal in punch_signals:
            cpp_content += f"uint8_t* {signal}, "
        cpp_content = cpp_content[:-2] + ")\n{\n"
        i = 0
        for signal in punch_signals:
            cpp_content += f"    *{signal} = fuzzers[{i}]->Congest() & 0x1;\n"
        cpp_content += "}"

        with open(f"{module_name}_dpi.cpp", "w") as f:
            f.write(cpp_content)

    def __insert_gate(self, module_name, verilog_code, signal, punch_signal):
        is_input_port = is_signal_input(verilog_code, signal)
        is_output_port = is_signal_output(verilog_code, signal)

        match = re.search(REGEX_STRING_MATCH_FULL_MODULE.format(module_name), verilog_code, re.DOTALL)
        if not match:
            err_message = f"Module '{module_name}' not found in the Verilog code."
            raise ValueError(err_message)

        module_body = match.group(1)

        match = re.search(REGEX_STRING_MATCH_MODULE_PORTS.format(module_name), verilog_code, re.DOTALL)
        module_definition = match.group(0)

        # Check if the signal exists in the module. It is quite possible that the signal in the port
        # is never used in the implementation. Thus, output the warning.
        if not re.search(REGEX_STRING_MATCH_SIGNAL.format(signal), module_body):
            err_message = f"Warning: Signal '{signal}' not found in module '{module_name}'."
            raise ValueError(err_message)

        # Modify the signal to include the gate.
        modified_signal = f"modified_{signal}"

        if is_output_port:
            gate_logic = f"    assign {signal} = {modified_signal} & {punch_signal};\n"
            modified_body = re.sub(rf"(?<!\w){signal}(?!\w)", modified_signal, module_body)
        else:
            gate_logic = f"    wire {modified_signal};\n"
            gate_logic += f"    assign {modified_signal} = {signal} & {punch_signal};\n"

            if is_input_port:
                modified_body = re.sub(rf"(?<!\w){signal}(?!\w)", modified_signal, module_body)
            else:
                modified_body = replace_internal_signal(signal, module_body)

        modified_body = gate_logic + modified_body
        modified_code = f"{module_definition}\n{modified_body}\nendmodule"

        return modified_code

    def __insert_gates(self, module_name, module_path, signals):
        with open(module_path, "r") as f:
            verilog_code = f.read()

        modified_code = verilog_code
        for s in signals:
            signal = s["name"]
            punch_signal = s["punch_name"]
            modified_code = self.__insert_gate(module_name, modified_code, signal, punch_signal)

        with open(module_path, "w") as f:
            f.write(modified_code)

    def __insert_dpi_calls(self, module_name, module_path, punch_signals, control_signals):
        import_init = f'import "DPI-C" function void init_{module_name}();'
        import_fuzz = f'import "DPI-C" function void fuzz_{module_name}('
        for signal in punch_signals:
            import_fuzz += f"output {signal}, "
        import_fuzz = import_fuzz[:-2] + ");"

        initial_block = "    initial begin\n"
        initial_block += f"        init_{module_name}();\n"
        initial_block += "    end\n"
        always_block = generate_dpi_always_block(control_signals, import_fuzz)

        with open(module_path, "r") as f:
            verilog_code = f.read()

        modified_code = add_dpi_calls(verilog_code, initial_block, always_block)
        modified_code = import_init + "\n" + import_fuzz + "\n\n" + modified_code

        with open(module_path, "w") as f:
            f.write(modified_code)

    def __patch_module(self, module_path, signals):
        module_name = signals[0]["module_name"]
        punch_signals = [signal["punch_name"] for signal in signals]
        control_signals = signals[0]["parent_module_control_signals"]
        self.__create_dpi(module_name, punch_signals)
        self.__insert_gates(module_name, module_path, signals)
        self.__insert_dpi_calls(module_name, module_path, punch_signals, control_signals)

    def patch(self):
        try:
            self.__preprocess()
            self.__backup()
            for module_path, signals in self.grouped_signals.items():
                self.__patch_module(module_path, signals)

            return ReturnCode.SUCCESS

        except Exception as e:
            print(f"Error patching module: {str(e)}")
            return ReturnCode.FAILURE
