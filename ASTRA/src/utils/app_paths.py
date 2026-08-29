import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_DATA_DIR = PROJECT_ROOT / "data"


def default_data_dir(environ=None, platform=None, home=None):
    """Return an update-safe, per-user location for ASTRA's private data."""
    values = os.environ if environ is None else environ
    platform_name = sys.platform if platform is None else str(platform)
    home_dir = Path.home() if home is None else Path(home)

    override = str(values.get("ASTRA_DATA_DIR", "") or "").strip()
    if override:
        return Path(override).expanduser()

    if platform_name.startswith("win"):
        base = values.get("LOCALAPPDATA") or values.get("APPDATA")
        if base:
            return Path(base) / "ASTRA"
        return home_dir / "AppData" / "Local" / "ASTRA"

    if platform_name == "darwin":
        return home_dir / "Library" / "Application Support" / "ASTRA"

    xdg_data_home = str(values.get("XDG_DATA_HOME", "") or "").strip()
    if xdg_data_home:
        return Path(xdg_data_home) / "astra"
    return home_dir / ".local" / "share" / "astra"


DATA_DIR = default_data_dir()
