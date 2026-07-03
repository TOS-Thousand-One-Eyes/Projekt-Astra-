class Modules:

    def __init__(self, logger):
        self.logger = logger
        self.modules = []

    def add_module(self, module):
        self.modules.append(module)

    def list_modules(self):
        return self.modules

    def start_all(self):
        for module in self.modules:
            try:
                module.start()
            except Exception as error:
                self.logger.error(f"Module '{self._module_name(module)}' failed to start: {error}")

    def stop_all(self):
        for module in self.modules:
            try:
                module.stop()
            except Exception as error:
                self.logger.error(f"Module '{self._module_name(module)}' failed to stop: {error}")

    @staticmethod
    def _module_name(module):
        return getattr(module, "name", type(module).__name__)
