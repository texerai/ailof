# Copyright (c) 2024 texer.ai. All rights reserved.
import argparse
import json
import os
import sys

# Ailof code.
import source.vcd_parser as VcdParser
import source.design_explorer as DesignExplorer
import source.rtl_patcher as RtlPatcher
import source.llm_communicator as LLMCommunicator
import source.signal_explorer as SignalExplorer

# Constants.
BACKUP_FILE = "./backup/backup.json"

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Parse VCD files and extract design information.",
        epilog="Example usage: python script.py --vcd <vcd_file> --path <design_root_path>",
    )

    # Adding mandatory arguments
    parser.add_argument(
        "-v",
        "--vcd",
        required=False,
        help="path to the VCD file to be processed.",
    )

    parser.add_argument(
        "-p",
        "--path",
        required=False,
        help="path to the root directory of the design files.",
    )

    parser.add_argument(
        "-u",
        "--undo",
        required=False,
        action='store_true',
        help="undo the patching, restore backed up files.",
    )

    # Parse the arguments
    if len(sys.argv) == 1:
        parser.print_help()
        return False, "", ""

    args = parser.parse_args()

    if not args.undo:
        if not args.path or not args.vcd:
            parser.print_help()
            return False, "", ""

    return True, args.vcd, args.path, args.undo


def main():
    # Get arguments.
    is_parsed, vcd_file_path, design_root_path, should_undo = parse_arguments()

    if should_undo:
        if os.path.exists(BACKUP_FILE):
            with open(BACKUP_FILE, "r") as infile:
                backed_up_data = json.load(infile)
                for file, code in backed_up_data.items():
                    with open(file, "w") as outfile:
                        outfile.write(code)
            os.remove(BACKUP_FILE)
    # Parse VCD.
    elif is_parsed:
        vcd_parser = VcdParser.VcdParser()
        json_design_hierarchy = vcd_parser.parse(vcd_file_path, design_root_path)

        explorer = DesignExplorer.DesignExplorer(json_design_hierarchy)
        selected_modules = explorer.run()

        print(selected_modules)
        llm_communicator = LLMCommunicator.LLMCommunicator(selected_modules)
        modules_with_signals = llm_communicator.run()

        signal_explorer = SignalExplorer.SignalExplorer(modules_with_signals)
        selected_signals = signal_explorer.run()

        print(selected_signals)
        rtl_patcher = RtlPatcher.RtlPatcher(json_design_hierarchy, selected_modules, selected_signals)
        rtl_patcher.patch()

main()
