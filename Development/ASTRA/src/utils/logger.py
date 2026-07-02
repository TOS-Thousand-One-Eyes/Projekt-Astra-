from datetime import datetime

class Logger:
   
    def __init__(self):
        self.logs = []
   
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log = f"[{timestamp}] {message}"
        self.logs.append(log)
        print(log)
   
    def get_logs(self):
        return self.logs