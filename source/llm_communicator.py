# Copyright (c) 2024 texer.ai. All rights reserved.

import json
import ollama
import sys
import time
import re

ROLE = "You are a Verilog design verification expert specializing in signal analysis and testability."
PROMPT = """
<document>
    <source>{}</source>
    <targets>{}</targets>
    <document_content>
        {}
    </document_content>
</document>

Given a Verilog processor module and a list of target signals, identify which signals 
can be safely fuzzed without affecting core functionality. Consider only signals from 
the provided list. A signal is considered safe if:
- It can be tied to constants (0/1) without breaking the design
- It can be modified through AND/OR gates while maintaining correct operation

Focus on internal signals of these types:
- Handshake/flow control signals
- Status flags (ready, busy, full)
- Debug/monitoring signals
- Optional feature controls
- Performance-related signals

Respond with ONLY valid JSON in the following format, without any additional text:
{{
    "signals": [
        {{
            "name": string,            // Use local signal name without hierarchy
            "certainty": integer,      // Fuzzing safety confidence (0-100)
            "explanation": string,     // Justification for fuzzing safety
            "fuzz_method": string,     // "tie_constant"|"logic_gates"|"both"
            "safe_value": string       // If tie_constant: "0"|"1"|"either"
        }}
    ],
    "note": string  // Optional. Include only for critical design observations
                    // or potential edge cases. Keep to one sentence.
}}

Exclude:
- Instance ports (connections to submodule instances)
- Any signals that might affect functionality under specific conditions

Do not include any explanatory text before or after the JSON output.
"""

TOKEN_LIMIT = 80000


class LLMCommunicator:
    def __init__(self, modules, model_name="qwen2.5:14b"):
        """
        Initialize with a dictionary of modules and a model name for Ollama.
        The 'modules' dict is expected to have the following structure per module:
            {
                "declaration_path": <path to Verilog file>,
                "signal_width_data": { <signal_name>: <width>, ... }
            }
        """
        self.modules = modules
        self.model_name = model_name
        sys.stdout.write("\x1b[2J\x1b[H")
        print(f"LLMCommunicator is initialized with {len(modules)} modules to process using model: {self.model_name}\n")

    def __read_module_content(self, module_path):
        try:
            with open(module_path, "r") as f:
                return f.read()
        except (IOError, FileNotFoundError) as e:
            raise FileNotFoundError(f"Could not read module at {module_path}: {str(e)}")

    def count_module_tokens(self, module_content):
        # Simple token count approximation: count whitespace-separated tokens.
        return len(module_content.split())

    def clean_json_response(self, response_text):
        """
        Remove markdown formatting, code blocks, and comments from the response.
        """
        content = response_text.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        content = content.strip()
        content = re.sub(r'\s*//.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^[\s\n]*```.*?```[\s\n]*$', '', content, flags=re.MULTILINE | re.DOTALL)
        return content

    def analyze_module(self, module_path, signals, module_content):
        module_name = module_path.split("/")[-1]
        print(f"\nAnalyzing module: {module_path}")
        # Format the prompt with the module name, the list of target signals, and file content.
        prompt = PROMPT.format(module_name, list(signals), module_content)
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": ROLE},
                    {"role": "user", "content": prompt},
                ]
                # Removed unsupported 'max_tokens' and 'temperature' parameters.
            )
            # Get the response text and clean it up
            response_text = response.message.content
            cleaned_response = self.clean_json_response(response_text)
            data = json.loads(cleaned_response)
            if "signals" not in data:
                raise ValueError(f"Unexpected JSON structure: {cleaned_response}")

            # Only include signals that are in the provided target list.
            validated_signals = [signal for signal in data["signals"] if signal["name"] in signals]
            print(f"Successfully analyzed {module_path}: found {len(validated_signals)} signals.")
            if "note" in data:
                print(f"Note: {data['note']}")

            return validated_signals

        except Exception as e:
            raise RuntimeError(f"Error while analyzing {module_path}: {str(e)}")

    def run(self):
        print("Starting module analysis...")
        total_tokens = 0
        last_request_time = time.time()

        for module_name, module_info in self.modules.items():
            path = module_info["declaration_path"]
            rtl_patcher_signals = module_info["signal_width_data"].keys()
            content = self.__read_module_content(path)
            num_tokens = self.count_module_tokens(content)

            # If approaching token limit, wait to avoid rate limiting.
            if total_tokens + num_tokens >= TOKEN_LIMIT:
                time_since_last = time.time() - last_request_time
                if time_since_last < 60:
                    wait_time = 60 - time_since_last
                    print(f"\nApproaching rate limit. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                total_tokens = 0
                last_request_time = time.time()

            total_tokens += num_tokens
            llm_com_signals = self.analyze_module(path, rtl_patcher_signals, content)
            self.modules[module_name]["signals"] = llm_com_signals

        print(f"\nAnalysis complete. Processed {len(self.modules)} modules.\n")
        return self.modules


if __name__ == "__main__":
    # Example modules dictionary.
    # In a real system, this would be provided by another part of your system.
    modules = {
        "module1": {
            "declaration_path": "rtl/module1.v",  # Replace with the actual path to your file.
            "signal_width_data": {"signal_a": 1, "signal_b": 2},
        },
        "module2": {
            "declaration_path": "rtl/module2.v",  # Replace with the actual path to your file.
            "signal_width_data": {"signal_c": 1, "signal_d": 2},
        },
    }

    # Set the desired model here.
    model_name = "qwen2.5:14b"
    communicator = LLMCommunicator(modules, model_name=model_name)
    results = communicator.run()
    print(json.dumps(results, indent=4))
