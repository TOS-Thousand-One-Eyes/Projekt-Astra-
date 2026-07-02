class Modules:

    def __init__(self):
        self.modules = []

    def add_module(self, module):
        self.modules.append(module)

    def list_modules(self):
        return self.modules

    def start_all(self):
        for module in self.modules:
            module.start()

    def stop_all(self):
        for module in self.modules:
            module.stop()
