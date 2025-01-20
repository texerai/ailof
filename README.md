# Ailof: **AI** assisted **Lo**gic **F**uzzer

## Overview
A Logic Fuzzer is a way to add extra harmless logic inside a hardware design so that it can reach and test more of its hidden internal states. This extra logic does not change what the processor does from the outside, but it makes the processor’s insides behave differently behind the scenes. The technique was proven to be effective and reported [here](https://dl.acm.org/doi/10.1145/3466752.3480092). Ailof leverages LLMs and classical ML approaches to make LF integration easy and maximize the effectiveness of the technique.

## Who is this tool for?
This tool is ideal for verification and design engineers who closely work with RTL, have implemented a verification environment, and feel relatively confident in the design’s functional correctness. It targets teams looking to push their verification beyond the usual coverage limits, adding extra stress and trying to expose hidden corner cases. Although it’s particularly well-suited for microprocessor projects that incorporate co-simulation techniques, the tool’s benefits extend to any complex design featuring intricate internal handshakes and interactions.

## How to set up Ailof?
1. Install the Anthropic Python API library.
 Run the following command in your terminal to install: 
   ``` python -m pip install anthropic```
2. Set essential environmental variables.
3. Set the Anthropic API key to interact with LLM.
 Run the following command in your terminal to set the key:
   ```export ANTHROPIC_API_KEY="sk-your-anthropic-api-key"```

# How to run Ailof?
 Run the following command in your terminal inside the `/ailof` directory:
  ```python ailof.py --vcd <path_to_vcd_file> --flist <path_to_flist_file>```
  