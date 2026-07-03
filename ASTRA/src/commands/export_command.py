import json
import os
from datetime import datetime
from pathlib import Path

from commands.base import Command

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
EXPORT_DIR = DATA_DIR / "exports"


class ExportCommand(Command):

    TRIGGERS = ("export",)
    help_text = "- export - save a copy of your memory and config to a file"

    def __init__(self, config, memory, export_dir=EXPORT_DIR, logger=None):
        super().__init__(logger)
        self.config = config
        self.memory = memory
        self.export_dir = Path(export_dir)

    def handle(self, message, normalized):
        if normalized not in self.TRIGGERS:
            return None

        now = datetime.now()
        data = {
            "exported_at": now.isoformat(timespec="seconds"),
            "config": {
                "name": self.config.name,
                "version": self.config.version,
                "log_level": self.config.log_level,
                "log_to_file": self.config.log_to_file,
                "check_for_updates": self.config.check_for_updates,
                "use_language_fallback": self.config.use_language_fallback,
                "language_base_url": self.config.language_base_url,
                "language_model": self.config.language_model,
            },
            "facts": self.memory.all_facts(),
            "long_memory": self.memory.recall_long(),
        }

        self.export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"astra_export_{now.strftime('%Y%m%d_%H%M%S_%f')}.json"
        path = self.export_dir / filename
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)

        return f"Exported your memory and config to {path}."
