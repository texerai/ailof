# Copyright (c) 2024 texer.ai. All rights reserved.
from models.model import DesignExplorerModel as Model
from views.terminal_view import DesignExplorerTerminalView as View
from controllers.terminal_controller import DesignExplorerController as Controller

def main():
    model = Model()
    view = View()
    controller = Controller(model, view)

    controller.run()

if __name__ == "__main__":
    main()
