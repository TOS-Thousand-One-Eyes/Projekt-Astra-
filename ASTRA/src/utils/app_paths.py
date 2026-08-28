"""Stable application paths that do not depend on the source checkout."""

import os
import platform
from pathlib import Path


SOURCE_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def user_data_dir(env=None, system=None, home=None):
    """Return Astra's persistent per-OS data directory.

    ``ASTRA_DATA_DIR`` is an explicit override for portable/test installs.
    The default deliberately lives outside the Git checkout so replacing or
    updating the source tree cannot erase profile PINs and personal memory.
    """
    environment = os.environ if env is None else env
    override = str(environment.get("ASTRA_DATA_DIR") or "").strip()
    if override:
        return Path(override).expanduser()

    system_name = str(system or platform.system()).casefold()
    home_dir = Path(home) if home is not None else Path.home()
    if system_name == "windows":
        base = environment.get("LOCALAPPDATA") or environment.get("APPDATA")
        return Path(base) / "Astra" if base else home_dir / "AppData" / "Local" / "Astra"
    if system_name == "darwin":
        return home_dir / "Library" / "Application Support" / "Astra"

    xdg_data = str(environment.get("XDG_DATA_HOME") or "").strip()
    base = Path(xdg_data).expanduser() if xdg_data else home_dir / ".local" / "share"
    return base / "astra"
