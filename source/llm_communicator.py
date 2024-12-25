# Copyright (c) 2024 texer.ai. All rights reserved.

import json
import anthropic

SYSTEM_PROMPT = """
Given the Verilog code of a processor module, identify the signals
that you think should not affect the functionality of the processor.
You should consider signals such as handshake signals (ready), FIFO
full signals, busy signals, etc. For each signal you propose, provide
the percentage of how certain you are the signal should not affect
the functional correctness of the processor.

Provide the output in JSON format with the following information:
1. Signal name.
2. Certainty in percentage.
3. One sentence explanation of why the signal should not affect the processor.

Output format example:
{
    "signals": [
        {
            "name": "signal_name",
            "certainty": 95,
            "explanation": "This is a handshake signal used only for flow control."
        }
    ]
}
"""


class LLMCommunicator:
    def __init__(self, modules):
        self.modules_to_process = modules
        self.modules_with_signals = {}
        self.client = anthropic.Anthropic()

    def _read_module_content(self, module_path):
        try:
            with open(module_path, "r") as f:
                return f.read()
        except (IOError, FileNotFoundError) as e:
            raise FileNotFoundError(
                f"Could not read module at {module_path}: {str(e)}"
            )

    def count_module_tokens(self, module_path):
        content = self._read_module_content(module_path)

        count = self.client.beta.messages.count_tokens(
            model="claude-3-5-sonnet-20241022",
            messages=[
                {"role": "user", "content": content},
            ],
        )
        return count.input_tokens

    def analyze_module(self, module_path):
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
                            "content": [{"type": "text", "text": content}],
                        }
                    ],
                )
                .content[0]
                .text
            )

            data = json.loads(response)
            if "signals" not in data:
                raise ValueError(f"Unexpected JSON structure: {response}")
            return data["signals"]

        except anthropic.APIError as e:
            raise RuntimeError(
                f"API error while analyzing {module_path}: {str(e)}"
            )
        except json.JSONDecodeError:
            raise ValueError(f"LLM response is not valid JSON: {response}")

    def run(self):
        for module_name, module_info in self.modules_to_process.items():
            signals = self.analyze_module(module_info["declaration_path"])
            self.modules_with_signals[module_name] = signals

        return self.modules_with_signals
