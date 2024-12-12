# Copyright (c) 2024 texer.ai. All rights reserved.
import json

class DesignExplorerModel:
    def __init__(self):
        self.json_design_hierarchy = {}
        self.design_module_list = []
        self.working_list = []
        self.command_buffer = ""

    def load_json_vcd_hierarchy(self, json_design_hierarchy):
        self.json_design_hierarchy = json_design_hierarchy

    def load_dummy_data(self):
        for i in range(5):
            self.design_module_list.append("chiptop.system.tile_prci_domain.tile_reset_domain_boom_tile.core.dispatcher.io_dis_uops_0_0_valid")
            self.design_module_list.append("chiptop.system.tile_prci_domain.tile_reset_domain_boom_tile.core.dispatcher.io_dis_uops_1_0_valid")
            self.design_module_list.append("chiptop.system.tile_prci_domain.tile_reset_domain_boom_tile.core.dispatcher.io_dis_uops_2_0_valid")
            self.design_module_list.append("chiptop.system.tile_prci_domain.tile_reset_domain_boom_tile.core.dispatcher.io_dis_uops_0_0_bits_rob_idx")
            self.design_module_list.append("chiptop.system.tile_prci_domain.tile_reset_domain_boom_tile.core.dispatcher.io_dis_uops_1_0_bits_rob_idx")
            self.design_module_list.append("chiptop.system.tile_prci_domain.tile_reset_domain_boom_tile.core.dispatcher.io_dis_uops_2_0_bits_rob_idx")
            self.design_module_list.append("chiptop.system.tile_prci_domain.tile_reset_domain_boom_tile.core.dispatcher.io_dis_uops_0_0_bits_debug_inst")
            self.design_module_list.append("chiptop.system.tile_prci_domain.tile_reset_domain_boom_tile.core.dispatcher.io_dis_uops_1_0_bits_debug_inst")
            self.design_module_list.append("chiptop.system.tile_prci_domain.tile_reset_domain_boom_tile.core.dispatcher.io_dis_uops_2_0_bits_debug_inst")
            self.design_module_list.append("chiptop.system.tile_prci_domain.tile_reset_domain_boom_tile.core.dispatcher.io_dis_uops_2_0_bits_debug_pc")

        self.working_list = self.design_module_list.copy()

    def get_model_range(self, start, end):
        if start >= end:
            return []
        if start < 0 or end < 0:
            return []
        if start >= len(self.design_module_list):
            return []

        if end > len(self.design_module_list):
            end = len(self.design_module_list)

        return self.design_module_list[start:end]

    def register_key(self, key):
        self.search_buffer += key

    def filter(self, keyword):
        self.working_list = []
        for item in self.design_module_list:
            if keyword in item:
                self.working_list.append(item)
