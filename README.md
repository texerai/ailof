# Ailof: **AI** assisted **Lo**gic **F**uzzer

## Overview
A Logic Fuzzer is a way to add extra harmless logic inside a hardware design so that it can reach and test more of its hidden internal states. This extra logic does not change what the processor does from the outside, but it makes the processor’s insides behave differently behind the scenes. The technique was proven to be effective and reported [here](https://dl.acm.org/doi/10.1145/3466752.3480092). Ailof leverages LLMs and classical ML approaches to make LF integration easy and maximize the effectiveness of the technique.

## Who is this tool for?
This tool is ideal for verification and design engineers who closely work with RTL, have implemented a verification environment, and feel relatively confident in the design’s functional correctness. It targets teams looking to push their verification beyond the usual coverage limits, adding extra stress and trying to expose hidden corner cases. Although it’s particularly well-suited for microprocessor projects that incorporate co-simulation techniques, the tool’s benefits extend to any complex design featuring intricate internal handshakes and interactions.

## How to set up Ailof?
To get started with Ailof, follow these steps to set up the tool and prepare it for use in your hardware design verification workflow:

### Step 1: Install the Anthropic Python API Library
Ailof relies on the Anthropic Python API to interact with its integrated Large Language Model (LLM). To install the library, run the following command in your terminal:
  ```bash 
  python -m pip install anthropic
  ```

### Step 2: Set Essential Environment Variables
Ensure that your system is configured with the required environment variables. These variables are necessary for Ailof to operate correctly.

### Step 3: Set the Anthropic API Key
To enable communication with the Anthropic API, you need to set your Anthropic API key as an environment variable. Run the following command in your terminal, replacing `"sk-your-anthropic-api-key"` with your actual API key:
  ```bash
  export ANTHROPIC_API_KEY="sk-your-anthropic-api-key"
  ```

## How to use Ailof?
Ailof is designed to streamline the process of integrating Logic Fuzzing (LF) into your hardware design verification workflow. Follow these steps to effectively use the tool:

### Step 1: Run Ailof
Navigate to the `/ailof` directory in your terminal and execute the following command:
  ```bash
  python ailof.py --vcd <path_to_vcd_file> --flist <path_to_flist_file>
  ```
Replace `<path_to_vcd_file>` with the path to your VCD (Value Change Dump) file and `<path_to_flist_file>` with the path to your file list (flist) containing the design files.

### Step 2: Select Modules for Fuzzing
After running the command, Ailof will prompt you to select the specific modules within your design that you would like to fuzz. Carefully choose the modules that you believe could benefit from additional internal state exploration.

### Step 3: Choose Fuzzable Signals
Ailof will leverage its integrated LLM to suggest a list of fuzzable signals within the selected modules. Review the provided suggestions and select the signals that you want to include in the fuzzing process. These signals will be targeted for the insertion of additional logic to enhance internal state exploration.

### Step 4: Integrate Generated DPI File
Once the fuzzable signals are selected, Ailof will generate a DPI (Direct Programming Interface) file. Add this generated DPI file to your Makefile to ensure it is included in your simulation environment.

### Step 5: Run Simulation
With the DPI file integrated into your Makefile, proceed to run your simulation as usual. The added fuzzing logic will now be active, allowing you to explore more internal states and potentially uncover hidden corner cases in your design.

By following these steps, you can effectively utilize Ailof to enhance your verification process, pushing beyond traditional coverage limits and uncovering deeper insights into your hardware design.