import queue
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from config.config import Config
from core.brain import Brain
from gui.presenter import QUICK_COMMANDS, low_hw_summary, model_state_summary, runtime_title
from memory.memory_manager import MemoryManager
from modules.language_module import LanguageModule
from modules.modules import Modules
from utils.logger import Logger
from utils.ollama_client import OllamaClient
from utils.update_checker import UpdateChecker
from vision.semantic_vision import LocalVisionDescriber


class GuiLogger(Logger):
    def __init__(self, events, **kwargs):
        super().__init__(**kwargs)
        self.events = events

    def _print(self, entry):
        body = entry.split("] ", 1)[1] if "] " in entry else entry
        if body.startswith("CHAT "):
            self.events.put(("assistant", body[5:]))
        else:
            self.events.put(("system", entry))


def build_brain(config, logger):
    memory = MemoryManager()
    modules = Modules(logger)

    if config.use_language_fallback:
        language_client = OllamaClient(
            config.language_base_url,
            config.language_model,
            generate_timeout=config.language_generate_timeout,
        )
        modules.add_module(LanguageModule(language_client, logger))

    vision_describer = None
    if config.use_vision_model:
        vision_client = OllamaClient(
            config.vision_base_url,
            config.vision_model,
            generate_timeout=config.vision_generate_timeout,
        )
        vision_describer = LocalVisionDescriber(client=vision_client, source="vision")

    update_checker = UpdateChecker(config.version, logger) if config.check_for_updates else None
    brain = Brain(
        logger,
        config,
        memory,
        modules,
        update_checker=update_checker,
        vision_describer=vision_describer,
    )
    return brain


def language_module_from(brain):
    if not brain:
        return None
    for module in brain.modules.list_modules():
        if getattr(module, "name", None) == "language":
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

        self.title_var = tk.StringVar(value="ASTRA")
        self.status_var = tk.StringVar(value="Starting runtime...")
        self.detail_var = tk.StringVar(value=low_hw_summary())

        self._build_style()
        self._build_layout()
        self._set_controls_enabled(False)
        self._start_runtime()
        self.root.after(80, self._process_events)

    def _build_style(self):
        self.root.title("ASTRA")
        self.root.geometry("920x640")
        self.root.minsize(720, 480)
        self.root.configure(bg="#f5f7f8")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Root.TFrame", background="#f5f7f8")
        style.configure("Panel.TFrame", background="#ffffff", borderwidth=1, relief="solid")
        style.configure("Header.TLabel", background="#f5f7f8", foreground="#172026", font=("Segoe UI", 18, "bold"))
        style.configure("Subtle.TLabel", background="#f5f7f8", foreground="#5b6670", font=("Segoe UI", 10))
        style.configure("Status.TLabel", background="#ffffff", foreground="#0f766e", font=("Segoe UI", 11, "bold"))
        style.configure("Detail.TLabel", background="#ffffff", foreground="#4b5563", font=("Segoe UI", 9))
        style.configure("Action.TButton", padding=(10, 6), font=("Segoe UI", 9))
        style.configure("Send.TButton", padding=(14, 8), font=("Segoe UI", 10, "bold"))

    def _build_layout(self):
        shell = ttk.Frame(self.root, style="Root.TFrame", padding=16)
        shell.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)

        header = ttk.Frame(shell, style="Root.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, textvariable=self.title_var, style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Local-first assistant", style="Subtle.TLabel").grid(row=1, column=0, sticky="w")

        status = ttk.Frame(shell, style="Panel.TFrame", padding=12)
        status.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        status.columnconfigure(1, weight=1)
        ttk.Label(status, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(status, textvariable=self.detail_var, style="Detail.TLabel").grid(row=0, column=1, sticky="w", padx=(16, 0))

        quick = ttk.Frame(status, style="Panel.TFrame")
        quick.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.quick_buttons = []
        for index, (label, command) in enumerate(QUICK_COMMANDS):
            button = ttk.Button(
                quick,
                text=label,
                style="Action.TButton",
                command=lambda value=command: self.submit(value),
            )
            button.grid(row=0, column=index, padx=(0, 8))
            self.quick_buttons.append(button)
        self.restart_button = ttk.Button(
            quick,
            text="Restart Runtime",
            style="Action.TButton",
            command=self.restart_runtime,
        )
        self.restart_button.grid(row=0, column=len(QUICK_COMMANDS), padx=(8, 0))

        chat_panel = ttk.Frame(shell, style="Panel.TFrame", padding=1)
        chat_panel.grid(row=2, column=0, sticky="nsew")
        chat_panel.columnconfigure(0, weight=1)
        chat_panel.rowconfigure(0, weight=1)

        self.chat = ScrolledText(
            chat_panel,
            wrap="word",
            state="disabled",
            relief="flat",
            borderwidth=0,
            bg="#ffffff",
            fg="#172026",
            insertbackground="#172026",
            font=("Segoe UI", 10),
            padx=14,
            pady=12,
        )
        self.chat.grid(row=0, column=0, sticky="nsew")
        self.chat.tag_configure("user_label", foreground="#0f766e", font=("Segoe UI", 9, "bold"), spacing1=8)
        self.chat.tag_configure("assistant_label", foreground="#7c3aed", font=("Segoe UI", 9, "bold"), spacing1=8)
        self.chat.tag_configure("system_label", foreground="#b45309", font=("Segoe UI", 9, "bold"), spacing1=8)
        self.chat.tag_configure("user", foreground="#102a43", lmargin1=16, lmargin2=16, spacing3=4)
        self.chat.tag_configure("assistant", foreground="#243b53", lmargin1=16, lmargin2=16, spacing3=4)
        self.chat.tag_configure("system", foreground="#64748b", lmargin1=16, lmargin2=16, spacing3=4)

        input_row = ttk.Frame(shell, style="Root.TFrame")
        input_row.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        input_row.columnconfigure(0, weight=1)
        self.entry = ttk.Entry(input_row, font=("Segoe UI", 11))
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipady=6)
        self.entry.bind("<Return>", lambda _event: self.submit_entry())
        self.send_button = ttk.Button(input_row, text="Send", style="Send.TButton", command=self.submit_entry)
        self.send_button.grid(row=0, column=1)

    def _start_runtime(self):
        self.status_var.set("Starting runtime...")
        self.detail_var.set(low_hw_summary())
        self.worker_running = True
        threading.Thread(target=self._runtime_worker, daemon=True).start()

    def _runtime_worker(self):
        try:
            config = Config()
            logger = GuiLogger(
                self.events,
                level=config.log_level,
                log_to_file=config.log_to_file,
            )
            brain = build_brain(config, logger)
            brain.start()
        except Exception as error:
            self.events.put(("system", f"Runtime failed: {type(error).__name__}: {error}"))
            self.events.put(("runtime_failed", None))
            return
        self.events.put(("runtime_ready", (config, logger, brain)))

    def restart_runtime(self):
        if self.worker_running:
            return
        self._set_controls_enabled(False)
        self._append("system", "System", "Restarting ASTRA runtime...")
        try:
            if self.brain and self.brain.is_running:
                self.brain.stop()
        except Exception as error:
            self.events.put(("system", f"Runtime stop failed: {type(error).__name__}: {error}"))
        self.config = None
        self.logger = None
        self.brain = None
        self._start_runtime()

    def submit_entry(self):
        self.submit(self.entry.get())

    def submit(self, message):
        message = " ".join(str(message).split())
        if not message or self.worker_running or not self.brain:
            return
        self.entry.delete(0, "end")
        self._append("user", "You", message)
        self.worker_running = True
        self._set_controls_enabled(False)
        threading.Thread(target=self._command_worker, args=(message,), daemon=True).start()

    def _command_worker(self, message):
        try:
            self.brain.receive(message)
        except Exception as error:
            self.events.put(("system", f"Command failed: {type(error).__name__}: {error}"))
        finally:
            self.events.put(("command_done", None))

    def _process_events(self):
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "system":
                self._append("system", "System", payload)
            elif event == "assistant":
                self._append("assistant", "ASTRA", payload)
            elif event == "runtime_ready":
                self.config, self.logger, self.brain = payload
                self.title_var.set(runtime_title(self.config))
                self.worker_running = False
                self._refresh_status()
                self._set_controls_enabled(True)
                self.entry.focus_set()
            elif event == "runtime_failed":
                self.worker_running = False
                self.status_var.set("Runtime failed")
                self.detail_var.set("Fix the startup error and restart the GUI.")
                self._set_controls_enabled(False)
            elif event == "command_done":
                self.worker_running = False
                self._refresh_status()
                self._set_controls_enabled(bool(self.brain and self.brain.is_running))

        self.root.after(80, self._process_events)

    def _refresh_status(self):
        summary = model_state_summary(self.config, language_module_from(self.brain))
        self.status_var.set(summary["status"])
        self.detail_var.set(summary["detail"])

    def _set_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.entry.configure(state=state)
        self.send_button.configure(state=state)
        for button in self.quick_buttons:
            button.configure(state=state)
        restart_state = "disabled" if self.worker_running else "normal"
        self.restart_button.configure(state=restart_state)

    def _append(self, tag, label, text):
        clean = str(text).strip()
        if not clean:
            return
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{label}\n", f"{tag}_label")
        self.chat.insert("end", clean + "\n\n", tag)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def close(self):
        try:
            if self.brain and self.brain.is_running:
                self.brain.stop()
        finally:
            self.root.destroy()


def main():
    root = tk.Tk()
    app = AstraTkApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
