# Copyright (c) 2024 texer.ai. All rights reserved.
import argparse
import sys

# Ailof code.
import source.vcd_parser as VcdParser
import source.design_explorer as DesignExplorer
import source.llm_communicator as LLMCommunicator


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Parse VCD files and extract design information.",
        epilog="Example usage: python script.py --vcd <vcd_file> --path <design_root_path>",
    )

    # Adding mandatory arguments
    parser.add_argument(
        "-v",
        "--vcd",
        required=True,
        help="path to the VCD file to be processed.",
    )

    parser.add_argument(
        "-p",
        "--path",
        required=True,
        help="path to the root directory of the design files.",
    )

    # Parse the arguments
    if len(sys.argv) == 1:
        parser.print_help()
        return False, "", ""

    args = parser.parse_args()

    return True, args.vcd, args.path


def main():
    # Get arguments.
    is_parsed, vcd_file_path, design_root_path = parse_arguments()

    # Parse VCD.
    if is_parsed:
        vcd_parser = VcdParser.VcdParser()
        json_design_hierarchy = vcd_parser.parse(vcd_file_path, design_root_path)

        explorer = DesignExplorer.DesignExplorer(json_design_hierarchy)
        selected_modules = explorer.run()

        llm_communicator = LLMCommunicator.LLMCommunicator(selected_modules)
        modules_with_signals = llm_communicator.run()

        print(modules_with_signals)


main()
