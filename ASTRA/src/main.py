from core.brain import Brain
from utils.logger import Logger

def main():
   
    logger = Logger()
    brain = Brain(logger)
   
    brain.start()

if __name__ == "__main__":
    main()