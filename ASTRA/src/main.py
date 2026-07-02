from config.config import Config
from core.brain import Brain
from utils.logger import Logger

def main():
    logger = Logger()
    config = Config()
    brain = Brain(logger, config)
   
    brain.start()

if __name__ == "__main__":
    main()