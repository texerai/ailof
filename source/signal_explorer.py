# Copyright (c) 2024 texer.ai. All rights reserved.
from source.models.signal_model import SignalExplorerModel as Model
from source.views.signal_view import SignalExplorerTerminalView as View
from source.controllers.signal_controller import SignalExplorerController as Controller


class SignalExplorer:
    def __init__(self, all_signals):
        self.model = Model()
        self.model.load_signals(all_signals)
        self.view = View()
        self.controller = Controller(self.model, self.view)

    def run(self):
        return self.controller.run()
