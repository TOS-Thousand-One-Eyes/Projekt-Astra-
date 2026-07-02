from config.config import Config
from core.brain import Brain
from utils.logger import Logger
from memory.memory import Memory

def main():
    logger = Logger()
    config = Config()   
    memory = Memory()
    brain = Brain(logger, config, memory)
   
    brain.start()
    
if __name__ == "__main__":
    main()