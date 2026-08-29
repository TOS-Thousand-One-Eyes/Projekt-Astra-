from utils.app_paths import user_data_dir


def test_explicit_data_dir_override_wins():
    assert user_data_dir(
        env={"ASTRA_DATA_DIR": "/portable/astra", "LOCALAPPDATA": "/ignored"},
        system="Windows",
        home="/home/test",
    ).as_posix() == "/portable/astra"


def test_windows_data_lives_in_local_app_data():
    assert user_data_dir(
        env={"LOCALAPPDATA": "C:/Users/Erik/AppData/Local"},
        system="Windows",
        home="C:/Users/Erik",
    ).as_posix() == "C:/Users/Erik/AppData/Local/Astra"


def test_linux_data_uses_xdg_data_home():
    assert user_data_dir(
        env={"XDG_DATA_HOME": "/var/user-data"},
        system="Linux",
        home="/home/erik",
    ).as_posix() == "/var/user-data/astra"


def test_linux_data_has_home_fallback():
    assert user_data_dir(
        env={}, system="Linux", home="/home/erik"
    ).as_posix() == "/home/erik/.local/share/astra"
