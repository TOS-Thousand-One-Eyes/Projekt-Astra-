import json
import os
import queue
import threading
import uuid
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from config.config import Config
from core.brain import Brain
from gui.presenter import (
    GUI_THEMES,
    QUICK_COMMANDS,
    low_hw_summary,
    model_state_summary,
    normalize_theme,
    runtime_title,
    theme_button_label,
)
from learning.learning_manager import LearningManager
from learning.self_learning import SelfLearningManager
from memory.memory_manager import MemoryManager
from modules.language_module import LanguageModule
from modules.modules import Modules
from utils.logger import Logger
from utils.ollama_client import OllamaClient
from utils.update_checker import UpdateChecker
from vision.screen_observer import ScreenObserverModule
from vision.semantic_vision import LocalVisionDescriber


class GuiLogger(Logger):
    def __init__(
        self,
        events,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.events = events

    def _print(self, entry):
        body = (
            entry.split("] ", 1)[1]
            if "] " in entry
            else entry
        )
        if body.startswith("CHAT "):
            self.events.put(
                ("assistant", body[5:])
            )
        else:
            self.events.put(
                ("system", entry)
            )


def build_brain(config, logger):
    memory = MemoryManager()
    modules = Modules(logger)

    language_module = None
    language_client = None
    if config.use_language_fallback:
        language_client = OllamaClient(
            config.language_base_url,
            config.language_model,
            generate_timeout=(
                config.language_generate_timeout
            ),
            options={
                "num_ctx": config.language_num_ctx,
                "temperature": (
                    config.language_temperature
                ),
            },
            keep_alive=(
                config.language_keep_alive
            ),
        )
        language_module = LanguageModule(
            language_client,
            logger,
        )
        modules.add_module(
            language_module
        )

    vision_describer = None
    if config.use_vision_model:
        if (
            language_client
            and config.vision_base_url.rstrip("/")
            == config.language_base_url.rstrip("/")
            and config.vision_model
            == config.language_model
        ):
            vision_client = language_client
            source = "shared-language"
        else:
            vision_client = OllamaClient(
                config.vision_base_url,
                config.vision_model,
                generate_timeout=(
                    config.vision_generate_timeout
                ),
                options={
                    "num_ctx": config.vision_num_ctx,
                    "temperature": 0.1,
                },
                keep_alive=(
                    config.language_keep_alive
                ),
            )
            source = "vision"
        vision_describer = LocalVisionDescriber(
            client=vision_client,
            source=source,
        )
    elif language_client:
        vision_describer = LocalVisionDescriber(
            client=language_client,
            source="language",
        )

    learning = LearningManager(
        language_module=language_module
    )
    self_learning = SelfLearningManager(
        mode=config.self_learning_mode
    )

    screen_observer = ScreenObserverModule(
        describer=vision_describer,
        self_learning=self_learning,
        logger=logger,
        enabled=config.screen_observer_enabled,
        poll_seconds=(
            config.screen_observer_poll_seconds
        ),
        min_analysis_interval=(
            config.screen_observer_min_analysis_interval
        ),
        change_threshold=(
            config.screen_observer_change_threshold
        ),
        notify_threshold=(
            config.screen_observer_notify_threshold
        ),
        notification_cooldown=(
            config.screen_observer_notification_cooldown
        ),
    )
    modules.add_module(
        screen_observer
    )

    update_checker = (
        UpdateChecker(
            config.version,
            logger,
        )
        if config.check_for_updates
        else None
    )

    brain = Brain(
        logger,
        config,
        memory,
        modules,
        update_checker=update_checker,
        learning=learning,
        self_learning=self_learning,
        vision_describer=vision_describer,
        screen_observer=screen_observer,
    )
    return brain


def language_module_from(brain):
    if not brain:
        return None
    for module in brain.modules.list_modules():
        if getattr(
            module, "name", None
        ) == "language":
            return module
    return None


class AstraTkApp:
    def __init__(self, root):
        self.root = root
        self.events = queue.Queue()
        self.config = None
        self.logger = None
        self.brain = None
        self.worker_running = False
        self.model_refresh_running = False

        self.bootstrap_config = Config()
        self.theme_name = normalize_theme(
            getattr(self.bootstrap_config, "gui_theme", "dark")
        )
        self.style = None

        self.title_var = tk.StringVar(
            value="ASTRA"
        )
        self.status_var = tk.StringVar(
            value="Starting runtime..."
        )
        self.detail_var = tk.StringVar(
            value=low_hw_summary()
        )
        self.model_var = tk.StringVar(
            value=""
        )

        self._build_style()
        self._build_layout()
        self._apply_theme(self.theme_name, persist=False)
        self._set_controls_enabled(
            False
        )
        self._start_runtime()
        self.root.after(
            80,
            self._process_events,
        )

    def _build_style(self):
        self.root.title("ASTRA")
        self.root.geometry("980x680")
        self.root.minsize(760, 520)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_theme_styles()

    def _configure_theme_styles(self):
        palette = GUI_THEMES[self.theme_name]
        self.root.configure(bg=palette["root"])

        self.style.configure(
            "Root.TFrame",
            background=palette["root"],
        )
        self.style.configure(
            "Panel.TFrame",
            background=palette["panel"],
            bordercolor=palette["border"],
            borderwidth=1,
            relief="solid",
        )
        self.style.configure(
            "Header.TLabel",
            background=palette["root"],
            foreground=palette["text"],
            font=("Segoe UI", 18, "bold"),
        )
        self.style.configure(
            "Subtle.TLabel",
            background=palette["root"],
            foreground=palette["subtle"],
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Status.TLabel",
            background=palette["panel"],
            foreground=palette["status"],
            font=("Segoe UI", 11, "bold"),
        )
        self.style.configure(
            "Detail.TLabel",
            background=palette["panel"],
            foreground=palette["subtle"],
            font=("Segoe UI", 9),
        )
        for style_name, padding, font in (
            ("Action.TButton", (10, 6), ("Segoe UI", 9)),
            ("Send.TButton", (14, 8), ("Segoe UI", 10, "bold")),
        ):
            self.style.configure(
                style_name,
                background=palette["button"],
                foreground=palette["text"],
                bordercolor=palette["border"],
                padding=padding,
                font=font,
            )
            self.style.map(
                style_name,
                background=[
                    ("active", palette["button_active"]),
                    ("pressed", palette["button_active"]),
                    ("disabled", palette["button_disabled"]),
                ],
                foreground=[("disabled", palette["subtle"])],
            )

        self.style.configure(
            "App.TEntry",
            fieldbackground=palette["entry"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
        )
        self.style.configure(
            "App.TCombobox",
            fieldbackground=palette["entry"],
            background=palette["button"],
            foreground=palette["text"],
            arrowcolor=palette["text"],
            bordercolor=palette["border"],
        )
        self.style.map(
            "App.TCombobox",
            fieldbackground=[("readonly", palette["entry"])],
            selectbackground=[("readonly", palette["entry"])],
            selectforeground=[("readonly", palette["text"])],
            foreground=[("readonly", palette["text"])],
        )

        # Combobox dropdown is a Tk Listbox, not ttk, so theme it globally.
        self.root.option_add("*TCombobox*Listbox.background", palette["entry"])
        self.root.option_add("*TCombobox*Listbox.foreground", palette["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", palette["selection"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", palette["text"])

    def _apply_theme(self, theme, persist=False):
        self.theme_name = normalize_theme(theme)
        self._configure_theme_styles()
        palette = GUI_THEMES[self.theme_name]

        if hasattr(self, "chat"):
            self.chat.configure(
                bg=palette["panel"],
                fg=palette["text"],
                insertbackground=palette["text"],
                selectbackground=palette["selection"],
                selectforeground=palette["text"],
            )
            self.chat.tag_configure("user_label", foreground=palette["user_label"])
            self.chat.tag_configure("assistant_label", foreground=palette["assistant_label"])
            self.chat.tag_configure("system_label", foreground=palette["system_label"])
            self.chat.tag_configure("user", foreground=palette["user_text"])
            self.chat.tag_configure("assistant", foreground=palette["assistant_text"])
            self.chat.tag_configure("system", foreground=palette["system_text"])
            try:
                self.chat.vbar.configure(
                    background=palette["button"],
                    activebackground=palette["button_active"],
                    troughcolor=palette["root"],
                )
            except (AttributeError, tk.TclError):
                pass

        if hasattr(self, "theme_button"):
            self.theme_button.configure(text=theme_button_label(self.theme_name))

        if persist:
            self._persist_theme()

    def toggle_theme(self):
        next_theme = "light" if self.theme_name == "dark" else "dark"
        self._apply_theme(next_theme, persist=True)

    def _persist_theme(self):
        config = self.config or self.bootstrap_config
        path = getattr(config, "path", None)
        if not path:
            return False
        try:
            payload = {}
            if path.exists():
                with open(path, "r", encoding="utf-8-sig") as file:
                    loaded = json.load(file)
                if isinstance(loaded, dict):
                    payload = loaded
            payload["gui_theme"] = self.theme_name
            tmp_path = path.with_suffix(
                f"{path.suffix}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}.theme.tmp"
            )
            with open(tmp_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2, ensure_ascii=False)
                file.write("\n")
            os.replace(tmp_path, path)
        except (OSError, json.JSONDecodeError) as error:
            if self.logger:
                self.logger.warning(f"Failed to persist GUI theme: {error}")
            return False

        self.bootstrap_config.gui_theme = self.theme_name
        if self.config:
            self.config.gui_theme = self.theme_name
        return True

    def _build_layout(self):
        shell = ttk.Frame(
            self.root,
            style="Root.TFrame",
            padding=16,
        )
        shell.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        self.root.columnconfigure(
            0,
            weight=1,
        )
        self.root.rowconfigure(
            0,
            weight=1,
        )
        shell.columnconfigure(
            0,
            weight=1,
        )
        shell.rowconfigure(
            2,
            weight=1,
        )

        header = ttk.Frame(
            shell,
            style="Root.TFrame",
        )
        header.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 12),
        )
        header.columnconfigure(
            0,
            weight=1,
        )
        ttk.Label(
            header,
            textvariable=self.title_var,
            style="Header.TLabel",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(
            header,
            text=(
                "Local-first assistant "
                "with source-backed learning"
            ),
            style="Subtle.TLabel",
        ).grid(
            row=1,
            column=0,
            sticky="w",
        )
        self.theme_button = ttk.Button(
            header,
            text=theme_button_label(self.theme_name),
            style="Action.TButton",
            command=self.toggle_theme,
        )
        self.theme_button.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e",
            padx=(12, 0),
        )

        status = ttk.Frame(
            shell,
            style="Panel.TFrame",
            padding=12,
        )
        status.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 12),
        )
        status.columnconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            status,
            textvariable=self.status_var,
            style="Status.TLabel",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(
            status,
            textvariable=self.detail_var,
            style="Detail.TLabel",
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(16, 0),
        )

        quick = ttk.Frame(
            status,
            style="Panel.TFrame",
        )
        quick.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )
        self.quick_buttons = []
        for index, (
            label,
            command,
        ) in enumerate(QUICK_COMMANDS):
            button = ttk.Button(
                quick,
                text=label,
                style="Action.TButton",
                command=(
                    lambda value=command:
                    self.submit(value)
                ),
            )
            button.grid(
                row=0,
                column=index,
                padx=(0, 8),
            )
            self.quick_buttons.append(
                button
            )

        self.restart_button = ttk.Button(
            quick,
            text="Restart Runtime",
            style="Action.TButton",
            command=self.restart_runtime,
        )
        self.restart_button.grid(
            row=0,
            column=len(
                QUICK_COMMANDS
            ),
            padx=(8, 0),
        )

        model_row = ttk.Frame(
            status,
            style="Panel.TFrame",
        )
        model_row.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(10, 0),
        )
        model_row.columnconfigure(
            1,
            weight=1,
        )
        ttk.Label(
            model_row,
            text="Model:",
            style="Detail.TLabel",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
        )
        self.model_combo = ttk.Combobox(
            model_row,
            textvariable=self.model_var,
            state="readonly",
            width=42,
            style="App.TCombobox",
        )
        self.model_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 8),
        )
        self.model_apply_button = ttk.Button(
            model_row,
            text="Use",
            style="Action.TButton",
            command=self.apply_selected_model,
        )
        self.model_apply_button.grid(
            row=0,
            column=2,
            padx=(0, 8),
        )
        self.model_refresh_button = ttk.Button(
            model_row,
            text="Refresh",
            style="Action.TButton",
            command=self.refresh_models,
        )
        self.model_refresh_button.grid(
            row=0,
            column=3,
        )

        chat_panel = ttk.Frame(
            shell,
            style="Panel.TFrame",
            padding=1,
        )
        chat_panel.grid(
            row=2,
            column=0,
            sticky="nsew",
        )
        chat_panel.columnconfigure(
            0,
            weight=1,
        )
        chat_panel.rowconfigure(
            0,
            weight=1,
        )

        self.chat = ScrolledText(
            chat_panel,
            wrap="word",
            state="disabled",
            relief="flat",
            borderwidth=0,
            bg=GUI_THEMES[self.theme_name]["panel"],
            fg=GUI_THEMES[self.theme_name]["text"],
            insertbackground=GUI_THEMES[self.theme_name]["text"],
            font=("Segoe UI", 10),
            padx=14,
            pady=12,
        )
        self.chat.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        self.chat.tag_configure(
            "user_label",
            foreground=GUI_THEMES[self.theme_name]["user_label"],
            font=(
                "Segoe UI",
                9,
                "bold",
            ),
            spacing1=8,
        )
        self.chat.tag_configure(
            "assistant_label",
            foreground=GUI_THEMES[self.theme_name]["assistant_label"],
            font=(
                "Segoe UI",
                9,
                "bold",
            ),
            spacing1=8,
        )
        self.chat.tag_configure(
            "system_label",
            foreground=GUI_THEMES[self.theme_name]["system_label"],
            font=(
                "Segoe UI",
                9,
                "bold",
            ),
            spacing1=8,
        )
        self.chat.tag_configure(
            "user",
            foreground=GUI_THEMES[self.theme_name]["user_text"],
            lmargin1=16,
            lmargin2=16,
            spacing3=4,
        )
        self.chat.tag_configure(
            "assistant",
            foreground=GUI_THEMES[self.theme_name]["assistant_text"],
            lmargin1=16,
            lmargin2=16,
            spacing3=4,
        )
        self.chat.tag_configure(
            "system",
            foreground=GUI_THEMES[self.theme_name]["system_text"],
            lmargin1=16,
            lmargin2=16,
            spacing3=4,
        )

        input_row = ttk.Frame(
            shell,
            style="Root.TFrame",
        )
        input_row.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(12, 0),
        )
        input_row.columnconfigure(
            0,
            weight=1,
        )
        self.entry = ttk.Entry(
            input_row,
            font=(
                "Segoe UI",
                11,
            ),
            style="App.TEntry",
        )
        self.entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 10),
            ipady=6,
        )
        self.entry.bind(
            "<Return>",
            lambda _event:
            self.submit_entry(),
        )
        self.send_button = ttk.Button(
            input_row,
            text="Send",
            style="Send.TButton",
            command=self.submit_entry,
        )
        self.send_button.grid(
            row=0,
            column=1,
        )

    def _start_runtime(self):
        self.status_var.set(
            "Starting runtime..."
        )
        self.detail_var.set(
            low_hw_summary()
        )
        self.worker_running = True
        threading.Thread(
            target=self._runtime_worker,
            daemon=True,
        ).start()

    def _runtime_worker(self):
        try:
            config = Config()
            logger = GuiLogger(
                self.events,
                level=config.log_level,
                log_to_file=(
                    config.log_to_file
                ),
            )
            brain = build_brain(
                config,
                logger,
            )
            brain.start()
        except Exception as error:
            self.events.put(
                (
                    "system",
                    f"Runtime failed: "
                    f"{type(error).__name__}: {error}",
                )
            )
            self.events.put(
                ("runtime_failed", None)
            )
            return
        self.events.put(
            (
                "runtime_ready",
                (
                    config,
                    logger,
                    brain,
                ),
            )
        )

    def restart_runtime(self):
        if self.worker_running:
            return
        self._set_controls_enabled(
            False
        )
        self._append(
            "system",
            "System",
            "Restarting ASTRA runtime...",
        )
        try:
            if (
                self.brain
                and self.brain.is_running
            ):
                self.brain.stop()
        except Exception as error:
            self.events.put(
                (
                    "system",
                    f"Runtime stop failed: "
                    f"{type(error).__name__}: {error}",
                )
            )
        self.config = None
        self.logger = None
        self.brain = None
        self.model_var.set("")
        self.model_combo["values"] = ()
        self._start_runtime()

    def submit_entry(self):
        self.submit(
            self.entry.get()
        )

    def submit(self, message):
        message = " ".join(
            str(message).split()
        )
        if (
            not message
            or self.worker_running
            or not self.brain
        ):
            return
        self.entry.delete(
            0,
            "end",
        )
        self._append(
            "user",
            "You",
            message,
        )
        self.worker_running = True
        self._set_controls_enabled(
            False
        )
        threading.Thread(
            target=self._command_worker,
            args=(message,),
            daemon=True,
        ).start()

    def _command_worker(self, message):
        try:
            self.brain.receive(
                message
            )
        except Exception as error:
            self.events.put(
                (
                    "system",
                    f"Command failed: "
                    f"{type(error).__name__}: {error}",
                )
            )
        finally:
            self.events.put(
                ("command_done", None)
            )

    def refresh_models(self):
        if (
            self.model_refresh_running
            or not self.brain
        ):
            return
        self.model_refresh_running = True
        self.model_refresh_button.configure(
            state="disabled"
        )
        threading.Thread(
            target=self._model_refresh_worker,
            daemon=True,
        ).start()

    def _model_refresh_worker(self):
        try:
            module = language_module_from(
                self.brain
            )
            client = (
                getattr(
                    module,
                    "client",
                    None,
                )
                if module
                else None
            )
            if client is None and self.config:
                client = OllamaClient(
                    self.config.language_base_url,
                    self.config.language_model,
                    health_timeout=3,
                    generate_timeout=(
                        self.config.language_generate_timeout
                    ),
                )
            if not client:
                raise RuntimeError(
                    "No Ollama client is configured."
                )
            models = client.list_models()
            names = [
                item["name"]
                for item in models
            ]
            current = (
                getattr(client, "model", "")
                or ""
            )
            self.events.put(
                (
                    "model_list_ready",
                    (
                        names,
                        current,
                    ),
                )
            )
        except Exception as error:
            self.events.put(
                (
                    "model_list_error",
                    str(error),
                )
            )

    def apply_selected_model(self):
        selected = (
            self.model_var.get().strip()
        )
        if not selected:
            return
        self.submit(
            f"model use {selected}"
        )

    def _process_events(self):
        while True:
            try:
                event, payload = (
                    self.events.get_nowait()
                )
            except queue.Empty:
                break

            if event == "system":
                self._append(
                    "system",
                    "System",
                    payload,
                )
            elif event == "assistant":
                self._append(
                    "assistant",
                    "ASTRA",
                    payload,
                )
            elif event == "runtime_ready":
                (
                    self.config,
                    self.logger,
                    self.brain,
                ) = payload
                self.title_var.set(
                    runtime_title(
                        self.config
                    )
                )
                self._apply_theme(
                    getattr(self.config, "gui_theme", self.theme_name),
                    persist=False,
                )
                self.worker_running = False
                self._refresh_status()
                self._set_controls_enabled(
                    True
                )
                self.entry.focus_set()
                self.refresh_models()
            elif event == "runtime_failed":
                self.worker_running = False
                self.status_var.set(
                    "Runtime failed"
                )
                self.detail_var.set(
                    "Fix the startup error and restart the GUI."
                )
                self._set_controls_enabled(
                    False
                )
            elif event == "command_done":
                self.worker_running = False
                self._refresh_status()
                self._set_controls_enabled(
                    bool(
                        self.brain
                        and self.brain.is_running
                    )
                )
                self.refresh_models()
            elif event == "model_list_ready":
                names, current = payload
                self.model_refresh_running = False
                self.model_combo["values"] = names
                if current in names:
                    self.model_var.set(
                        current
                    )
                elif names:
                    self.model_var.set(
                        names[0]
                    )
                self._set_controls_enabled(
                    bool(
                        self.brain
                        and self.brain.is_running
                    )
                )
            elif event == "model_list_error":
                self.model_refresh_running = False
                self.model_refresh_button.configure(
                    state="normal"
                )
                self.events.put(
                    (
                        "system",
                        f"Model list unavailable: {payload}",
                    )
                )

        self.root.after(
            80,
            self._process_events,
        )

    def _refresh_status(self):
        summary = model_state_summary(
            self.config,
            language_module_from(
                self.brain
            ),
        )
        self.status_var.set(
            summary["status"]
        )
        self.detail_var.set(
            summary["detail"]
        )

    def _set_controls_enabled(
        self,
        enabled,
    ):
        state = (
            "normal"
            if enabled
            else "disabled"
        )
        self.entry.configure(
            state=state
        )
        self.send_button.configure(
            state=state
        )
        for button in self.quick_buttons:
            button.configure(
                state=state
            )
        self.theme_button.configure(
            state=state
        )

        self.model_combo.configure(
            state=(
                "readonly"
                if enabled
                else "disabled"
            )
        )
        self.model_apply_button.configure(
            state=state
        )
        self.model_refresh_button.configure(
            state=(
                "disabled"
                if self.model_refresh_running
                else state
            )
        )

        restart_state = (
            "disabled"
            if self.worker_running
            else "normal"
        )
        self.restart_button.configure(
            state=restart_state
        )

    def _append(
        self,
        tag,
        label,
        text,
    ):
        clean = str(text).strip()
        if not clean:
            return
        self.chat.configure(
            state="normal"
        )
        self.chat.insert(
            "end",
            f"{label}\n",
            f"{tag}_label",
        )
        self.chat.insert(
            "end",
            clean + "\n\n",
            tag,
        )
        self.chat.configure(
            state="disabled"
        )
        self.chat.see("end")

    def close(self):
        try:
            if (
                self.brain
                and self.brain.is_running
            ):
                self.brain.stop()
        finally:
            self.root.destroy()


def main():
    root = tk.Tk()
    app = AstraTkApp(root)
    root.protocol(
        "WM_DELETE_WINDOW",
        app.close,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
