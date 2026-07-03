from datetime import datetime
from pathlib import Path

LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
LOG_FILE = Path(__file__).resolve().parents[2] / "data" / "astra.log"


class Logger:

    def __init__(self, level="INFO", log_to_file=False, log_path=LOG_FILE):
        self.level = level if level in LEVELS else "INFO"
        self.log_to_file = log_to_file
        self.log_path = Path(log_path)
        self.logs = []

    def log(self, message, level="INFO"):
        if level not in LEVELS:
            level = "INFO"
        if LEVELS.index(level) < LEVELS.index(self.level):
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {level} {message}"
        self.logs.append(entry)
        try:
            print(entry)
        except UnicodeEncodeError:
            print(entry.encode("ascii", errors="replace").decode("ascii"))
        if self.log_to_file:
            try:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(entry + "\n")
            except OSError as error:
                self.log_to_file = False
                failure_entry = f"[{timestamp}] WARNING Logging to file failed ({error}); file logging disabled for this session."
                self.logs.append(failure_entry)
                print(failure_entry)

    def debug(self, message):
        self.log(message, "DEBUG")

    def info(self, message):
        self.log(message, "INFO")

    def warning(self, message):
        self.log(message, "WARNING")

    def error(self, message):
        self.log(message, "ERROR")

    def get_logs(self):
        return self.logs
