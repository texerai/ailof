# Copyright (c) 2024 texer.ai. All rights reserved.
class SignalExplorerModel:
    def __init__(self):
        self.all_signals = {}
        self.selected_signals = {}
        self.control_signals = {}

    def flatten_data(self, modules_with_signals):
        flattened = {}
        for module, module_info in modules_with_signals.items():
            try:
                for signal in module_info["signals"]:
                    signal_name = signal["name"]
                    full_signal_name = f"{module}.{signal_name}"
                    signal_info = signal.copy()
                    signal_info["width"] = module_info["signal_width_data"][signal_name]
                    signal_info["module_name"] = module_info["module_name"]
                    signal_info["declaration_path"] = module_info["declaration_path"]
                    flattened[full_signal_name] = signal_info
            except Exception as e:
                print(f"Warning: {e}")
        return flattened

    def load_signals(self, all_signals):
        self.all_signals = self.flatten_data(all_signals["modules_with_signals"])
        self.control_signals = all_signals["control_signals"]
        i = 0
        for signal, data in self.all_signals.items():
            self.selected_signals[i] = f"{signal} | Fuzzing safety confidence: {data['certainty']}"
            i += 1
        self.filter("")

    def filter(self, keyword):
        self.working_list = []
        self.working_list_ids = []
        keyword_lower = keyword.lower()
        for id, item in self.selected_signals.items():
            if keyword_lower in item.lower():
                self.working_list_ids.append(id)
                self.working_list.append(item)
