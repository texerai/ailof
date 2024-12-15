# Copyright (c) 2024 texer.ai. All rights reserved.
from source.models.model import DesignExplorerModel as Model
from source.views.terminal_view import DesignExplorerTerminalView as View
from source.controllers.terminal_controller import DesignExplorerController as Controller

class DesignExplorer:
    def __init__(self, json_design_hierarchy):
        self.model = Model()
        self.model.load_json_design_hierarchy(json_design_hierarchy)
        self.view = View()
        self.controller = Controller(self.model, self.view)

    def run(self):
        self.controller.run()
