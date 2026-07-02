class Modules:
   
    def __init__(self):
        self.modules = ["Module1", "Module2"]
   
    def add_module(self, module):
        self.modules.append(module)
   
    def list_modules(self):
        return self.modules