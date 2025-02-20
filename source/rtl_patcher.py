# Copyright (c) 2024 texer.ai. All rights reserved.
import json
import random
import re
import sys

from source.enums import ReturnCode

REGEX_STRING_MATCH_SPEC_MODULE_BEGIN = r"module\s+{}(?:\s+import\s+[\w:.*]+;)?(?:\s*#\(\s*([\s\S]*?)\s*\))?\s*\("
REGEX_STRING_MATCH_SIGNAL = r"(?<![\w.]){}\b(?![\w.])"
REGEX_STRING_MATCH_INSTANCE_BEGIN = r"{}\ +(#\([^;]*?\))?\s+\)\ {}\ +\("
REGEX_STRING_MATCH_ALL_MODULES = r"(\w+)\s*#?\s*\([^;]*?\)\s*(\w+)\s*\(\s*(?:[^;]*?)\s*\)\s*;"
REGEX_STRING_MATCH_IMPORT_FUNCTION = r'import "DPI-C" function void (\w+)\s*\(([^)]*)\);'

BACKUP_FILE = "./backup.json"


def is_signal(verilog_code, signal, port_type):
    pattern = rf"{port_type}\s+(?:[\w:]+\s+)*(?:\[[^\]]+\]\s+)*{re.escape(signal)}\b"

    return bool(re.search(pattern, verilog_code, re.MULTILINE))


def extract_module_parts(verilog_code, module_name):
    # A function to extract the header, definition and body of the module from the Verilog code.
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

    # Find the semicolon after port list.
    pos = port_end
    while pos < len(verilog_code) and verilog_code[pos] != ";":
        pos += 1
    if pos >= len(verilog_code):
        return None, None, None

    module_definition = verilog_code[start_pos : pos + 1]

    # Find module body (everything between module definition and matching endmodule).
    body_start = pos + 1
    pos = body_start

    while pos < len(verilog_code):
        # Look for "endmodule" keyword.
        if verilog_code[pos:].lstrip().startswith("endmodule"):
            # Extract body excluding the endmodule keyword.
            module_body = verilog_code[body_start:pos].strip()
            return header_content, module_definition, module_body
        pos += 1

    return None, None, None


def restore_internal_signal_based_on_assignment(signal, module_body):
    # A function to restore the internal signal based on the assignment.
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
        assignment_target = left_part.split()[-1] if left_part.split() else ""

        right_part = line[op_pos:].strip()

        modified_left_part = left_part

        if f"modified_{signal}" == assignment_target:
            modified_left_part = " ".join(left_part.split()[:-1] + [signal])

        if left_part != modified_left_part:
            lines[i] = f"{modified_left_part} {right_part}"

    return "\n".join(lines)


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


def find_submodules_using_internal_signal(signal, verilog_code):
    # Finds all submodules that use the given signal as a parameter.

    lines = verilog_code.split("\n")
    code_without_comments = []
    original_lines = {}

    for i, line in enumerate(lines):
        # Remove single-line comments but keep the original
        cleaned_line = re.sub(r"//.*$", "", line)
        code_without_comments.append(cleaned_line)
        original_lines[i] = line

    # Rejoin the code
    code_without_comments = "\n".join(code_without_comments)

    results = []

    # Find all module instantiations with their port connections

    for match in re.finditer(REGEX_STRING_MATCH_ALL_MODULES, code_without_comments, re.DOTALL | re.MULTILINE):
        instance_name = match.group(2)
        instance_text = match.group(0)
        instance_start = match.start()

        # Find the specific port connection line - handle both input and output ports
        port_pattern = r"\.(\w+)(?:_[io])?(?:\s*\(\s*" + re.escape(signal) + r"\s*\)|\s*\(\s*" + re.escape(signal) + r"\s*\))"

        # Get all lines of this instance
        instance_lines = instance_text.split("\n")
        base_line_num = code_without_comments[:instance_start].count("\n")

        # Search each line for the port connection
        for i, line in enumerate(instance_lines):
            port_match = re.search(port_pattern, line)
            if port_match:
                port_name = port_match.group(1)
                line_number = base_line_num + i
                results.append((instance_name, port_name, original_lines[line_number]))

    return results


def identify_internal_port_type(verilog_code, signal):
    # A function to identify the type of the given signal.
    if is_signal(verilog_code, signal, "input"):
        return "input"
    elif is_signal(verilog_code, signal, "output"):
        return "output"
    else:
        return None


class RtlPatcher:
    def __init__(self, json_design_hierarchy, selected_modules, selected_signals):
        self.json_design_hierarchy = json_design_hierarchy
        self.selected_modules = selected_modules
        self.selected_signals = selected_signals
        self.grouped_signals = []
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

        temp_grouped_signals = {}

        for signal_path, signal_data in self.selected_signals.items():
            parent_module_path = signal_data["declaration_path"]
            module_hierarchy = ".".join(signal_path.split(".")[:-1])

            if parent_module_path not in temp_grouped_signals:
                temp_grouped_signals[parent_module_path] = {"module_hierarchy": module_hierarchy, "signals": []}
            temp_grouped_signals[parent_module_path]["signals"].append(signal_data)

        for module_path, data in temp_grouped_signals.items():
            self.grouped_signals.append((data["module_hierarchy"], module_path, data["signals"]))

    def __backup(self):
        # Create backups of all files that will be modified.
        backed_up_files = {}

        for _, parent_module_path, _ in self.grouped_signals:
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
        cpp_content += f"    for (size_t i = 0; i < {len(punch_signals)}; ++i)\n"
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
            i += 1
        cpp_content += "}"

        with open(f"{module_name}_dpi.cpp", "w") as f:
            f.write(cpp_content)

    def __insert_gate(self, module_hierarchy, module_name, verilog_code, signal, punch_signal):
        is_input_port = is_signal(verilog_code, signal, "input")
        is_output_port = is_signal(verilog_code, signal, "output")

        header_content, module_definition, module_body = extract_module_parts(verilog_code, module_name)

        if module_definition is None:
            err_message = f"Module '{module_name}' not found in the Verilog code."
            raise ValueError(err_message)

        # Check if the signal is used in the module.
        if not re.search(REGEX_STRING_MATCH_SIGNAL.format(signal), module_body):
            err_message = f"Warning: Signal '{signal}' not found in module '{module_name}'."
            raise ValueError(err_message)

        modified_signal = f"modified_{signal}"
        gate_logic = f"    logic {punch_signal};\n"

        # Insert the gate logic into the Verilog code.
        if is_output_port:
            gate_logic += f"    assign {signal} = {modified_signal} & {punch_signal};\n"
            modified_body = re.sub(rf"(?<!\w){signal}(?!\w)", modified_signal, module_body)
        else:
            gate_logic += f"    wire {modified_signal};\n"
            gate_logic += f"    assign {modified_signal} = {signal} & {punch_signal};\n"

            if is_input_port:
                modified_body = re.sub(rf"(?<!\w){signal}(?!\w)", modified_signal, module_body)
            else:
                modified_body = re.sub(
                    rf"((wire|reg|logic)\s+[^;]*\b{signal}\b)|(?<!\.|\w)\b{signal}\b(?!\s*;)",
                    lambda m: m.group(0) if m.group(1) else modified_signal,
                    module_body,
                )
                modified_body = restore_internal_signal_based_on_assignment(signal, modified_body)
                signal_usage = find_submodules_using_internal_signal(modified_signal, modified_body)

                for submodule_name, submodule_port_name, line_content in signal_usage:
                    submodule_hierarchy = f"{module_hierarchy}.{submodule_name}"

                    if submodule_hierarchy not in self.json_design_hierarchy:
                        print(
                            f"Warning: Submodule '{submodule_hierarchy}' in module '{module_name}' not found in design hierarchy. Ensure that:\n"
                            f"  1. The module declaration is included in the filelist\n"
                            f"  2. The module instance is present in the VCD dump\n"
                            f"Skipping submodule processing...\n"
                        )
                        modified_line = re.sub(rf"\(modified_{signal}\)", f"({signal})", line_content)
                        modified_body = modified_body.replace(line_content, modified_line)
                        continue

                    submodule_path = self.json_design_hierarchy[submodule_hierarchy]["declaration_path"]

                    with open(submodule_path, "r") as infile:
                        submodule_verilog_code = "".join(infile.readlines())

                    port_type = identify_internal_port_type(submodule_verilog_code, submodule_port_name)

                    if port_type == "output":
                        modified_line = re.sub(rf"\(modified_{signal}\)", f"({signal})", line_content)
                        modified_body = modified_body.replace(line_content, modified_line)

        modified_body = gate_logic + modified_body
        modified_code = f"{header_content}\n\n{module_definition}\n{modified_body}\nendmodule"

        return modified_code

    def __insert_gates(self, module_hierarchy, module_path, module_name, signals):
        with open(module_path, "r") as f:
            verilog_code = f.read()

        modified_code = verilog_code
        for s in signals:
            signal = s["name"]
            punch_signal = s["punch_name"]
            modified_code = self.__insert_gate(module_hierarchy, module_name, modified_code, signal, punch_signal)

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

    def __patch_module(self, module_hierarchy, module_path, signals):
        module_name = signals[0]["module_name"]
        punch_signals = [signal["punch_name"] for signal in signals]
        control_signals = signals[0]["parent_module_control_signals"]
        self.__create_dpi(module_name, punch_signals)
        self.__insert_gates(module_hierarchy, module_path, module_name, signals)
        self.__insert_dpi_calls(module_name, module_path, punch_signals, control_signals)

    def patch(self):
        try:
            self.__preprocess()
            self.__backup()
            for module_hierarchy, module_path, signals in self.grouped_signals:
                self.__patch_module(module_hierarchy, module_path, signals)

            return ReturnCode.SUCCESS

        except Exception as e:
            print("Error during RTL patching preparation:")
            print(f"  - Module: {module_hierarchy}")
            print(f"  - File: {module_path}")
            print(f"  - {str(e)}")
            print(f"  - {type(e).__name__}: {e.__traceback__.tb_lineno}")
            return ReturnCode.FAILURE
