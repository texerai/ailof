# Copyright (c) 2024 texer.ai. All rights reserved.

import json
import anthropic
import openai
import tiktoken
import sys
import time

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
can be safely fuzzed (randomized) without affecting core functionality. Consider only
signals from the provided list. A signal is considered safe if:
- It can be modified through AND/OR gates while maintaining correct operation.

Focus on internal signals of these types:
- Handshake/flow control signals
- Status flags (ready, busy, full)
- Debug/monitoring signals
- Optional feature controls
- Performance-related signals

Exclude:
- Instance ports (connections to submodule instances)

Also, identify the primary clock and reset signals that control synchronous logic.

Respond with ONLY valid JSON in the following format, without any additional text:
{{
    "fuzz_candidates": {{
        "signals": [
            {{
                "name": string,            // Use local signal name without hierarchy
                "certainty": integer,      // Fuzzing safety confidence (0-100)
                "explanation": string      // Justification for fuzzing safety
            }}
        ],
        "note": string  // Optional. Include only for critical design observations
                        // or potential edge cases. Keep to one sentence.
    }},
    "control_signals": {{
        "clock": string,    // Clock signal name
        "reset": string,    // Reset signal name
        "edge": string      // "posedge"|"negedge" for clock
    }}
}}

Do not include any explanatory text before or after the JSON output.
"""

TOKEN_LIMIT = 80000


class LLMCommunicator:
    def __init__(self, modules, model_type="openai"):
        self.modules = modules
        self.model_type = model_type
        sys.stdout.write("\x1b[2J\x1b[H")
        print(f"LLMCommunicator is initialized with {len(self.modules)} module(s) to process.\n")

    def __read_module_content(self, module_path):
        try:
            with open(module_path, "r") as f:
                return f.read()
        except (IOError, FileNotFoundError) as e:
            raise FileNotFoundError(f"Could not read module at {module_path}: {str(e)}")

    def count_module_tokens(self, module_content):
        if self.model_type == "openai":
            try:
                encoding = tiktoken.encoding_for_model("gpt-4o-2024-05-13")
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(module_content))
        else:
            return self.claude.beta.messages.count_tokens(
                model="claude-3-5-sonnet-20241022",
                messages=[
                    {"role": "user", "content": module_content},
                ],
            ).input_tokens

    def analyze_module(self, module_path, signals, module_content):
        module_name = module_path.split("/")[-1]
        print(f"\nAnalyzing module: {module_path}")
        try:
            if self.model_type == "openai":
                response_content = openai.ChatCompletion.create(
                    model="gpt-4o-2024-05-13",
                    max_tokens=1024,
                    temperature=0,
                    messages=[{"role": "system", "content": ROLE}, {"role": "user", "content": PROMPT.format(module_name, signals, module_content)}],
                    response_format={"type": "json_object"},
                )

                response = response_content.choices[0].message.content
            else:
                response = (
                    self.claude.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=1024,
                        temperature=0,
                        system=ROLE,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": PROMPT.format(module_name, signals, module_content),
                                    }
                                ],
                            }
                        ],
                    )
                    .content[0]
                    .text
                )

            data = json.loads(response)

            validated_fuzz_candidates = [signal for signal in data["fuzz_candidates"]["signals"] if signal["name"] in signals]
            control_signals = data["control_signals"]

            print(f"Successfully analyzed {module_path}: found {len(validated_fuzz_candidates)} signals.")
            if "note" in data["fuzz_candidates"]:
                print(f"Note: {data['fuzz_candidates']['note']}")

            return validated_fuzz_candidates, control_signals

        except anthropic.APIError as e:
            raise RuntimeError(f"API error while analyzing {module_path}: {str(e)}")
        except openai.BadRequestError as e:
            raise RuntimeError(f"API error while analyzing {module_path}: {str(e)}")
        except json.JSONDecodeError:
            raise ValueError(f"LLM response is not a valid JSON: {response_content}")

    def run(self):
        print("Starting module analysis...")
        total_tokens = 0
        last_request_time = time.time()

        for module_name, module_info in self.modules.items():
            path = module_info["declaration_path"]
            rtl_patcher_signals = module_info["signal_width_data"].keys()
            content = self.__read_module_content(path)
            num_tokens = self.count_module_tokens(content)

            if total_tokens + num_tokens >= TOKEN_LIMIT:
                time_since_last = time.time() - last_request_time
                if time_since_last < 60:
                    wait_time = 60 - time_since_last
                    print(f"\nApproaching rate limit. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)

                total_tokens = 0
                last_request_time = time.time()

            total_tokens += num_tokens
            fuzz_candidates, control_signals = self.analyze_module(path, rtl_patcher_signals, content)
            self.modules[module_name]["fuzz_candidates"] = fuzz_candidates
            self.modules[module_name]["control_signals"] = control_signals

        print(f"\nAnalysis complete. Processed {len(self.modules)} modules.\n")
        return self.modules
