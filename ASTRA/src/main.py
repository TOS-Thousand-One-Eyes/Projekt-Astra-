from config.config import Config
from core.brain import Brain
from utils.logger import Logger
from memory.memory import Memory
from modules.modules import Modules

def main():
    logger = Logger()
    config = Config()   
    memory = Memory()
    modules = Modules()
    brain = Brain(logger, config, memory, modules)
   
    brain.start()
    
if __name__ == "__main__":
    main()