# Copyright (c) 2024 texer.ai. All rights reserved.
import argparse
import json
import os

# Ailof code.
import source.vcd_parser as VcdParser
import source.design_explorer as DesignExplorer
import source.rtl_patcher as RtlPatcher
import source.llm_communicator as LLMCommunicator
import source.signal_explorer as SignalExplorer
import source.flist_formatter as FlistFormatter

from source.enums import ReturnCode


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Parse VCD and Flist files to extract design information.",
        epilog="Example usage: python script.py --vcd <vcd_file> --flist <flist_file>",
    )

    # Adding mandatory arguments
    parser.add_argument(
        "-v",
        "--vcd",
        required=False,
        help="path to the VCD file to be processed.",
    )

    parser.add_argument(
        "-f",
        "--flist",
        required=False,
        help="path to the Flist file to be processed.",
    )

    parser.add_argument(
        "-u",
        "--undo",
        required=False,
        action="store_true",
        help="undo the patching, restore backed up files.",
    )

    args = parser.parse_args()

    if not args.undo:
        if not args.flist or not args.vcd:
            parser.print_help()
            return False, "", "", ""

    return True, args.vcd, args.flist, args.undo


def main():
    # Get arguments.
    is_parsed, vcd_file_path, flist_file_path, should_undo = parse_arguments()

    if should_undo:
        if os.path.exists(RtlPatcher.BACKUP_FILE):
            with open(RtlPatcher.BACKUP_FILE, "r") as infile:
                backed_up_data = json.load(infile)
                for file, code in backed_up_data.items():
                    with open(file, "w") as outfile:
                        outfile.write(code)
            os.remove(RtlPatcher.BACKUP_FILE)
    # Parse VCD.
    elif is_parsed:
        formatter = FlistFormatter.FlistFormatter()
        flist = formatter.format_cva6(flist_file_path)

        vcd_parser = VcdParser.VcdParser()
        json_design_hierarchy = vcd_parser.parse(vcd_file_path, flist)

        explorer = DesignExplorer.DesignExplorer(json_design_hierarchy)
        selected_modules, return_code = explorer.run()

        if return_code == ReturnCode.SUCCESS:
            llm_communicator = LLMCommunicator.LLMCommunicator(selected_modules)
            modules_with_signals = llm_communicator.run()

            signal_explorer = SignalExplorer.SignalExplorer(modules_with_signals)
            selected_signals, return_code = signal_explorer.run()

            if return_code == ReturnCode.SUCCESS:
                rtl_patcher = RtlPatcher.RtlPatcher(json_design_hierarchy, selected_modules, selected_signals)
                is_patched, err_message = rtl_patcher.patch()
                if not is_patched:
                    print(err_message)


main()
