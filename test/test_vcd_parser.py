# Copyright (c) 2024 texer.ai. All rights reserved.
import os
import sys
import json
import subprocess

from source.vcd_parser import VcdParser

REPO_URL = "https://github.com/openhwgroup/cva6"

PATH_TO_EXPECTED_JSON = "test/test_files/jsons/expected_modules.json"
PATH_TO_NEW_JSON = "test/test_files/jsons/new_modules.json"

PATH_TO_DESIGN = "test/test_files/designs"
PATH_TO_VCD_FILE = "test/test_files/vcds/hello_world.cv32a65x.vcd"
PATH_TO_FLIST_FILE = ""

def clone_verilog_design(repo_url):
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    target_dir = os.path.join(os.getcwd(), PATH_TO_DESIGN, repo_name)
    
    if os.path.exists(target_dir):
        return
    
    parent_dir = os.path.join(os.getcwd(), PATH_TO_DESIGN)
    os.makedirs(parent_dir, exist_ok=True)

    try:
        subprocess.run(["git", "config", "--global", "http.postBuffer", "1048576000"], check=True)
        subprocess.run(["git", "clone", "--depth", "1", repo_url, target_dir], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while cloning the repository: {e}")

def compare_json(path_to_json):

    try:
        with open(path_to_json, 'r') as file:
            new_json = json.load(file)

        with open(PATH_TO_EXPECTED_JSON, 'r') as expected_file:
            expected_json = json.load(expected_file)

        if new_json != expected_json:
            sys.exit(1)
        else:
            print("Test cases passed successfully.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format: {e}")
        sys.exit(1)

if __name__ == "__main__":
    
    clone_verilog_design(REPO_URL)
    
    parser = VcdParser()
    parser.parse(PATH_TO_VCD_FILE, PATH_TO_FLIST_FILE)
    parser.export_json(PATH_TO_NEW_JSON)
    
    compare_json(PATH_TO_NEW_JSON)
    
    