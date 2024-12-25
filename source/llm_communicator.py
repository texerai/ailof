# Copyright (c) 2024 texer.ai. All rights reserved.

import json
import anthropic
import sys

SYSTEM_PROMPT = """
Given a Verilog processor module, identify signals that can be safely fuzzed
without affecting core functionality. A signal is considered safe if:
- It can be tied to constants (0/1) without breaking the design
- It can be modified through AND/OR gates while maintaining correct operation

Focus on:
- Handshake/flow control signals
- Status flags (ready, busy, full)
- Debug/monitoring signals
- Optional feature controls
- Performance-related signals

Respond with ONLY valid JSON in the following format, without any additional text:
{
    "signals": [
        {
            "name": string,            // Use local signal name without hierarchy
            "width": integer,
            "certainty": integer,      // 0-100 confidence score
            "explanation": string,     // Justification for fuzzing safety
            "fuzz_method": string,     // "tie_constant"|"logic_gates"|"both"
            "safe_value": string       // If tie_constant: "0"|"1"|"either"
        }
    ],
    "note": string  // Optional. Include only for critical design observations
                    // or potential edge cases. Keep to one sentence.
}

Exclude any signals that might affect functionality under specific conditions.
Do not include any explanatory text before or after the JSON output.
"""


class LLMCommunicator:
    def __init__(self, modules):
        self.modules = modules
        self.client = anthropic.Anthropic()
        sys.stdout.write("\x1b[2J\x1b[H")
        print(f"LLMCommunicator is initialized with {len(modules)} modules to process.\n")

    def _read_module_content(self, module_path):
        try:
            with open(module_path, "r") as f:
                return f.read()
        except (IOError, FileNotFoundError) as e:
            raise FileNotFoundError(f"Could not read module at {module_path}: {str(e)}")

    def count_module_tokens(self, module_path):
        content = self._read_module_content(module_path)

        count = self.client.beta.messages.count_tokens(
            model="claude-3-5-sonnet-20241022",
            messages=[
                {
                    "role": "user",
                    "content": content,
                },
            ],
        )
        return count.input_tokens

    def analyze_module(self, module_path):
        print(f"\nAnalyzing module: {module_path}")
        content = self._read_module_content(module_path)
        try:
            response = (
                self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    temperature=0,
                    system=SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": content,
                                }
                            ],
                        }
                    ],
                )
                .content[0]
                .text
            )

            data = json.loads(response)
            if "signals" not in data:
                raise ValueError(f"Unexpected JSON structure: {response}")
            print(f"Successfully analyzed {module_path}: found {len(data["signals"])} signals.")
            if "note" in data:
                print(f"Note: {data["note"]}")
            return data["signals"]

        except anthropic.APIError as e:
            raise RuntimeError(f"API error while analyzing {module_path}: {str(e)}")
        except json.JSONDecodeError:
            raise ValueError(f"LLM response is not valid JSON: {response}")

    def run(self):
        print("Starting module analysis...")
        for module_name, module_info in self.modules.items():
            signals = self.analyze_module(module_info["declaration_path"])
            self.modules[module_name]["signals"] = signals

        print(f"\nAnalysis complete. Processed {len(self.modules)} modules.\n")
        return self.modules
