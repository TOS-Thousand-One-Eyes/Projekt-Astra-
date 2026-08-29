from pathlib import Path

from utils.app_paths import default_data_dir


def test_windows_data_dir_uses_local_appdata_outside_the_checkout():
    path = default_data_dir(
        environ={"LOCALAPPDATA": r"C:\Users\Petr\AppData\Local"},
        platform="win32",
        home=Path(r"C:\Users\Petr"),
    )

    assert path == Path(r"C:\Users\Petr\AppData\Local") / "ASTRA"


def test_data_dir_can_be_explicitly_overridden():
    path = default_data_dir(
        environ={"ASTRA_DATA_DIR": r"D:\Private\AstraData"},
        platform="win32",
        home=Path(r"C:\Users\Petr"),
    )

    assert path == Path(r"D:\Private\AstraData")


def test_linux_data_dir_honors_xdg_data_home():
    path = default_data_dir(
        environ={"XDG_DATA_HOME": "/srv/user-data"},
        platform="linux",
        home=Path("/home/petr"),
    )

    assert path == Path("/srv/user-data/astra")
