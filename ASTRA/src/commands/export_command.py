import json
import os
import threading
import uuid
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
                "gui_theme": self.config.gui_theme,
                "use_language_fallback": self.config.use_language_fallback,
                "language_base_url": self.config.language_base_url,
                "language_model": self.config.language_model,
                "language_generate_timeout": self.config.language_generate_timeout,
                "language_num_ctx": self.config.language_num_ctx,
                "language_temperature": self.config.language_temperature,
                "language_keep_alive": self.config.language_keep_alive,
                "use_vision_model": self.config.use_vision_model,
                "vision_base_url": self.config.vision_base_url,
                "vision_model": self.config.vision_model,
                "vision_generate_timeout": self.config.vision_generate_timeout,
                "vision_num_ctx": self.config.vision_num_ctx,
                "self_learning_mode": self.config.self_learning_mode,
                "screen_observer_enabled": self.config.screen_observer_enabled,
                "screen_observer_poll_seconds": self.config.screen_observer_poll_seconds,
                "screen_observer_min_analysis_interval": self.config.screen_observer_min_analysis_interval,
                "screen_observer_change_threshold": self.config.screen_observer_change_threshold,
                "screen_observer_notify_threshold": self.config.screen_observer_notify_threshold,
                "screen_observer_notification_cooldown": self.config.screen_observer_notification_cooldown,
            },
            "facts": self.memory.all_facts(),
            "long_memory": self.memory.recall_long(),
        }

        self.export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"astra_export_{now.strftime('%Y%m%d_%H%M%S_%f')}.json"
        path = self.export_dir / filename
        tmp_path = path.with_suffix(
            f"{path.suffix}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}.tmp"
        )
        with open(tmp_path, "w", encoding="utf-8", errors="backslashreplace") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)

        return f"Exported your memory and config to {path}."
