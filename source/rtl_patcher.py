# Copyright (c) 2024 texer.ai. All rights reserved.
import json
import random
import re
import sys

from source.enums import ReturnCode

REGEX_STRING_MATCH_MODULE_BEGIN = r"(?i)\bmodule\s+(\w+)\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\(([^;]*?)\)\s*;"
REGEX_STRING_MATCH_FULL_MODULE = r"module\s+{}\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\([^;]*?\);\s*(.*?)\s*endmodule"
REGEX_STRING_MATCH_MODULE_PORTS = r"module\s+{}\s*(?:\s+import\s+[\w:]+(?:\*|[\w,]*)\s*;\s*)?\#?\s*\([^;]*?\);"
REGEX_STRING_MATCH_INPUT_SIGNAL = r"\binput\s+(?:wire|logic|reg)?\s*(?:\[.*?\]\s*)?(?:.*,\s*)*{}\s*(?=[,;])"
REGEX_STRING_MATCH_OUTPUT_SIGNAL = r"\boutput\s+(?:wire|logic|reg)?\s*(?:\[.*?\]\s*)?(?:.*,\s*)*{}\s*(?=[,;])"
REGEX_STRING_MATCH_SIGNAL = r"\b{}\b"
REGEX_STRING_MATCH_IMPORT_FUNCTION = r'import "DPI-C" function void (\w+)\s*\(([^)]*)\);'

BACKUP_FILE = "./backup.json"


def is_signal_input(verilog_code, signal):
    match = re.search(REGEX_STRING_MATCH_MODULE_BEGIN, verilog_code, re.DOTALL)
    if not match:
        return False

    module_declaration = match.group(0)
    if re.search(REGEX_STRING_MATCH_INPUT_SIGNAL.format(signal), module_declaration) is None:
        return False

    return True


def is_signal_output(verilog_code, signal):
    match = re.search(REGEX_STRING_MATCH_MODULE_BEGIN, verilog_code, re.DOTALL)
    if not match:
        return False

    module_declaration = match.group(0)
    if re.search(REGEX_STRING_MATCH_OUTPUT_SIGNAL.format(signal), module_declaration) is None:
        return False

    return True


def replace_internal_signal(signal, module_body):
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
