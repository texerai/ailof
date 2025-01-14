import os
import sys
import json
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from source.vcd_parser import VcdParser
from source.flist_formatter import FlistFormatter

REPO_URL = "https://github.com/openhwgroup/cva6"

PATH_TO_EXPECTED_JSON = "test/test_files/jsons/exp_vcd_parser_output.json"
PATH_TO_NEW_JSON = "test/test_files/jsons/new_vcd_parser_output.json"

PATH_TO_DESIGN = "test/test_files/designs"
PATH_TO_VCD_FILE = "test/test_files/vcds/hello_world.cv32a65x.vcd"
PATH_TO_FLIST_FILE = "test/test_files/flists/Flist.cva6"


def clone_verilog_design(repo_url):
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    target_dir = os.path.join(os.getcwd(), PATH_TO_DESIGN, repo_name)

    if os.path.exists(target_dir):
        return

    parent_dir = os.path.join(os.getcwd(), PATH_TO_DESIGN)
    os.makedirs(parent_dir, exist_ok=True)

    try:
        subprocess.run(["git", "config", "--global", "http.postBuffer", "1048576000"], check=True)
        subprocess.run(["git", "clone", "--recurse-submodules", "--depth", "1", repo_url, target_dir], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while cloning the repository: {e}")


def ___remove_prefix_from_path(json_obj):
    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            if key == "declaration_path" and isinstance(value, str):
                index = value.find("/cva6")
                if index != -1:
                    json_obj[key] = value[index:]
            elif isinstance(value, (dict, list)):
                ___remove_prefix_from_path(value)
    elif isinstance(json_obj, list):
        for item in json_obj:
            ___remove_prefix_from_path(item)
    return json_obj


def compare_json(path_to_json):
    try:
        with open(path_to_json, "r") as file:
            new_json = json.load(file)
            modified_new_json = ___remove_prefix_from_path(new_json)

        with open(PATH_TO_EXPECTED_JSON, "r") as expected_file:
            expected_json = json.load(expected_file)

        if modified_new_json == expected_json:
            print("Test cases passed successfully.")
        else:
            print("Error, files are different")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format: {e}")
        sys.exit(1)


if __name__ == "__main__":
    clone_verilog_design(REPO_URL)

    dirname = os.path.dirname(os.path.abspath(__file__))
    os.environ["TARGET_CFG"] = "build"
    os.environ["CVA6_REPO_DIR"] = dirname + "/test_files/designs/cva6"
    os.environ["HPDCACHE_DIR"] = dirname + "/test_files/designs/cva6/core/cache_subsystem/hpdcache"

    formatter = FlistFormatter()
    f_lists = formatter.format_cva6(PATH_TO_FLIST_FILE)

    parser = VcdParser()
    parser.parse(PATH_TO_VCD_FILE, f_lists)
    parser.export_json(PATH_TO_NEW_JSON)

    compare_json(PATH_TO_NEW_JSON)
