import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from utils.app_paths import SOURCE_DATA_DIR, user_data_dir


IDENTITY_SCHEMA = "astra-identity/profiles/v1"
PBKDF2_ITERATIONS = 310_000
MAX_PBKDF2_ITERATIONS = 2_000_000
DEFAULT_PROFILES = (
    ("erik", "Erik"),
    ("petr", "Petr"),
)
LEGACY_PRIVATE_FILES = ("long_memory.json", "facts.json", "astra.log")
LEGACY_PRIVATE_DIRS = (
    "actions",
    "automation",
    "experience",
    "learning",
    "self_learning",
)
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")
_PATH_LOCKS = {}
_PATH_LOCKS_GUARD = threading.Lock()


class IdentityStoreError(RuntimeError):
    """Raised when the profile store cannot be trusted or persisted."""


class AuthenticationError(ValueError):
    """Raised when a supplied local profile PIN is incorrect."""


class PinNotConfiguredError(AuthenticationError):
    """Raised when a profile still needs its first local PIN."""


@dataclass(frozen=True)
class UserIdentity:
    user_id: str
    display_name: str
    data_dir: Path


class IdentityManager:
    """
    Local profile selection and PIN verification.

    The PIN protects against accidental profile mix-ups. It is salted and
    hashed, but profile data itself is not encrypted and an operating-system
    administrator can still read the local files.
    """

    def __init__(self, data_dir=None, profiles=DEFAULT_PROFILES, legacy_data_dir=None):
        explicit_data_dir = data_dir is not None
        self.data_dir = Path(data_dir) if explicit_data_dir else user_data_dir()
        self.legacy_data_dir = Path(legacy_data_dir) if legacy_data_dir is not None else (
            self.data_dir if explicit_data_dir else SOURCE_DATA_DIR
        )
        self.root = self.data_dir / "identity"
        self.users_root = self.data_dir / "users"
        self.path = self.root / "profiles.json"
        self.migration_path = self.root / "legacy_migrations.json"
        self.lock_path = self.root / "profiles.lock"
        self._lock = path_lock(self.path)
        self._guard_state = threading.local()
        self._default_profiles = tuple(profiles)
        self.root.mkdir(parents=True, exist_ok=True)
        self.users_root.mkdir(parents=True, exist_ok=True)
        with self._store_guard():
            self._migrate_legacy_store()
            self._payload = self._load_or_create()

    def list_profiles(self):
        with self._store_guard():
            self._refresh_payload()
            return [
                {
                    "id": item["id"],
                    "display_name": item["display_name"],
                    "pin_configured": bool(item.get("pin")),
                    "last_seen_version": item.get("last_seen_version"),
                }
                for item in self._payload["profiles"]
            ]

    def resolve_profile(self, value):
        query = str(value or "").strip().casefold()
        if not query:
            raise KeyError("Profile name cannot be empty.")
        with self._store_guard():
            self._refresh_payload()
            for item in self._payload["profiles"]:
                if query in {item["id"].casefold(), item["display_name"].casefold()}:
                    return {
                        "id": item["id"],
                        "display_name": item["display_name"],
                        "pin_configured": bool(item.get("pin")),
                        "last_seen_version": item.get("last_seen_version"),
                    }
        raise KeyError(f"Unknown profile: {value}")

    def initialize_pin(self, user_id, pin):
        clean_pin = self._validate_pin(pin)
        with self._store_guard():
            self._refresh_payload()
            profile = self._profile(user_id)
            if profile.get("pin"):
                raise IdentityStoreError(
                    f"PIN is already configured for {profile['display_name']}."
                )
            profile["pin"] = self._hash_pin(clean_pin)
            profile["updated"] = timestamp()
            self._save_payload()
            return self._public_profile(profile)

    def authenticate(self, user_id, pin):
        with self._store_guard():
            self._refresh_payload()
            profile = self._profile(user_id)
            self._verify_pin(profile, pin)
            return self._open_session(profile)

    def change_pin(self, user_id, current_pin, new_pin):
        clean_pin = self._validate_pin(new_pin)
        with self._store_guard():
            self._refresh_payload()
            profile = self._profile(user_id)
            self._verify_pin(profile, current_pin)
            profile["pin"] = self._hash_pin(clean_pin)
            profile["updated"] = timestamp()
            self._save_payload()
            return self._public_profile(profile)

    def session_after_setup(self, user_id):
        """Open a session immediately after initialize_pin verified both entries."""
        with self._store_guard():
            self._refresh_payload()
            profile = self._profile(user_id)
            if not profile.get("pin"):
                raise PinNotConfiguredError(
                    f"{profile['display_name']} needs a PIN before login."
                )
            return self._open_session(profile)

    def last_seen_version(self, user_id):
        with self._store_guard():
            self._refresh_payload()
            return self._profile(user_id).get("last_seen_version")

    def mark_version_seen(self, user_id, version):
        clean_version = self._validate_version(version)
        with self._store_guard():
            self._refresh_payload()
            profile = self._profile(user_id)
            previous = profile.get("last_seen_version")
            if previous and version_tuple(previous) >= version_tuple(clean_version):
                return False
            profile["last_seen_version"] = clean_version
            profile["last_seen_at"] = timestamp()
            profile["updated"] = timestamp()
            self._save_payload()
            return True

    def migrate_legacy_data(self, user_id="erik"):
        """
        Copy pre-profile runtime data into Erik's private directory once.

        Original files are intentionally retained as a recoverable backup.
        Existing destination files are never overwritten.
        """
        normalized = self._normalize_id(user_id)
        if normalized != "erik":
            return []
        with self._store_guard():
            migrations = self._load_migrations()
            if migrations.get("legacy_private_data_to_erik_v1"):
                return []

            target_root = self.users_root / normalized
            target_root.mkdir(parents=True, exist_ok=True)
            copied = []
            for name in LEGACY_PRIVATE_FILES:
                source = self.legacy_data_dir / name
                target = target_root / name
                if source.is_file() and not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    copied.append(name)

            for name in LEGACY_PRIVATE_DIRS:
                source = self.legacy_data_dir / name
                target = target_root / name
                if source.is_dir():
                    copied.extend(
                        str(Path(name) / relative)
                        for relative in self._copy_missing_tree(source, target)
                    )

            migrations["legacy_private_data_to_erik_v1"] = {
                "completed": timestamp(),
                "copied": copied,
                "originals_retained": True,
            }
            self._atomic_json_write(self.migration_path, migrations)
            return copied

    def _open_session(self, profile):
        self.migrate_legacy_data(profile["id"])
        profile_dir = self.users_root / profile["id"]
        profile_dir.mkdir(parents=True, exist_ok=True)
        return UserIdentity(
            user_id=profile["id"],
            display_name=profile["display_name"],
            data_dir=profile_dir,
        )

    def _load_or_create(self):
        if self.path.exists():
            payload = self._read_json(self.path)
            return self._validate_payload(payload)

        now = timestamp()
        payload = {
            "schema": IDENTITY_SCHEMA,
            "profiles": [
                {
                    "id": self._normalize_id(user_id),
                    "display_name": str(display_name).strip(),
                    "pin": None,
                    "created": now,
                    "updated": now,
                }
                for user_id, display_name in self._default_profiles
            ],
        }
        self._payload = payload
        self._save_payload()
        return payload

    def _refresh_payload(self):
        if self.path.exists():
            self._payload = self._validate_payload(self._read_json(self.path))

    def _migrate_legacy_store(self):
        """Copy the old checkout-local identity/users tree once, without overwrites."""
        try:
            source = self.legacy_data_dir.resolve()
            target = self.data_dir.resolve()
        except OSError:
            source = self.legacy_data_dir.absolute()
            target = self.data_dir.absolute()
        if source == target or not self.legacy_data_dir.exists():
            return

        legacy_identity = self.legacy_data_dir / "identity"
        legacy_profiles = legacy_identity / "profiles.json"
        # Automatic import is only safe before the stable store exists. Once a
        # user has created a stable PIN, an old checkout must never merge stale
        # profile files back into that live identity.
        if self.path.exists() or not legacy_profiles.is_file():
            return

        legacy_migrations = legacy_identity / "legacy_migrations.json"
        if legacy_migrations.is_file() and not self.migration_path.exists():
            try:
                shutil.copy2(legacy_migrations, self.migration_path)
            except OSError as error:
                raise IdentityStoreError(
                    f"Could not migrate legacy {legacy_migrations.name}: {error}"
                ) from error
        legacy_users = self.legacy_data_dir / "users"
        if legacy_users.is_dir():
            try:
                self._copy_missing_tree(legacy_users, self.users_root)
            except OSError as error:
                raise IdentityStoreError(
                    f"Could not migrate legacy profile data: {error}"
                ) from error
        try:
            # Copy the identity last. If an earlier copy is interrupted, the
            # next launch can safely complete the missing user files and retry.
            shutil.copy2(legacy_profiles, self.path)
        except OSError as error:
            raise IdentityStoreError(
                f"Could not migrate legacy {legacy_profiles.name}: {error}"
            ) from error

    def _validate_payload(self, payload):
        if not isinstance(payload, dict) or payload.get("schema") != IDENTITY_SCHEMA:
            raise IdentityStoreError(
                f"{self.path.name} has an unsupported identity schema; refusing to reset it."
            )
        profiles = payload.get("profiles")
        if not isinstance(profiles, list) or not profiles:
            raise IdentityStoreError(
                f"{self.path.name} does not contain a valid profile list."
            )
        seen = set()
        for profile in profiles:
            if not isinstance(profile, dict):
                raise IdentityStoreError("Identity profile entry is not an object.")
            user_id = self._normalize_id(profile.get("id"))
            display_name = str(profile.get("display_name") or "").strip()
            if not display_name or user_id in seen:
                raise IdentityStoreError("Identity profiles contain a missing or duplicate ID.")
            seen.add(user_id)
            profile["id"] = user_id
            profile["display_name"] = display_name
            pin = profile.get("pin")
            if pin is not None and not self._valid_pin_record(pin):
                raise IdentityStoreError(
                    f"PIN record for {display_name} is invalid; refusing an unsafe reset."
                )
            last_seen = profile.get("last_seen_version")
            if last_seen is not None and not VERSION_PATTERN.fullmatch(str(last_seen)):
                raise IdentityStoreError(
                    f"Last-seen version for {display_name} is invalid."
                )
        return payload

    def _verify_pin(self, profile, pin):
        pin_record = profile.get("pin")
        if not pin_record:
            raise PinNotConfiguredError(
                f"{profile['display_name']} needs a PIN before login."
            )
        supplied = self._derive_pin(str(pin), pin_record)
        expected = str(pin_record.get("hash", ""))
        if not expected or not hmac.compare_digest(supplied, expected):
            raise AuthenticationError("Incorrect PIN.")

    def _profile(self, user_id):
        normalized = self._normalize_id(user_id)
        for item in self._payload["profiles"]:
            if item["id"] == normalized:
                return item
        raise KeyError(f"Unknown profile: {user_id}")

    @staticmethod
    def _public_profile(profile):
        return {
            "id": profile["id"],
            "display_name": profile["display_name"],
            "pin_configured": bool(profile.get("pin")),
            "last_seen_version": profile.get("last_seen_version"),
        }

    @staticmethod
    def _normalize_id(value):
        normalized = str(value or "").strip().casefold()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,31}", normalized):
            raise IdentityStoreError(f"Invalid profile ID: {value!r}")
        return normalized

    @staticmethod
    def _validate_pin(pin):
        text = str(pin or "")
        if not re.fullmatch(r"\d{4,12}", text):
            raise ValueError("PIN must contain 4 to 12 digits.")
        return text

    @staticmethod
    def _validate_version(version):
        text = str(version or "").strip()
        if not VERSION_PATTERN.fullmatch(text):
            raise ValueError("Version must use numeric major.minor.patch format.")
        return text

    @staticmethod
    def _hash_pin(pin):
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
        )
        return {
            "algorithm": "pbkdf2_sha256",
            "iterations": PBKDF2_ITERATIONS,
            "salt": salt.hex(),
            "hash": digest.hex(),
        }

    @staticmethod
    def _derive_pin(pin, record):
        if not IdentityManager._valid_pin_record(record):
            raise IdentityStoreError("Stored PIN metadata is invalid.")
        try:
            salt = bytes.fromhex(str(record["salt"]))
            iterations = int(record["iterations"])
        except (KeyError, TypeError, ValueError) as error:
            raise IdentityStoreError("Stored PIN metadata is invalid.") from error
        return hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            salt,
            iterations,
        ).hex()

    @staticmethod
    def _valid_pin_record(record):
        if not isinstance(record, dict):
            return False
        if record.get("algorithm") != "pbkdf2_sha256":
            return False
        try:
            iterations = int(record.get("iterations"))
            salt = bytes.fromhex(str(record.get("salt")))
            digest = bytes.fromhex(str(record.get("hash")))
        except (TypeError, ValueError):
            return False
        return (
            100_000 <= iterations <= MAX_PBKDF2_ITERATIONS
            and len(salt) >= 16
            and len(digest) == 32
        )

    def _save_payload(self):
        self._atomic_json_write(self.path, self._payload)

    @contextmanager
    def _store_guard(self):
        """Serialize profile reads/writes across threads and local processes."""
        with self._lock:
            depth = getattr(self._guard_state, "depth", 0)
            if depth:
                self._guard_state.depth = depth + 1
                try:
                    yield
                finally:
                    self._guard_state.depth -= 1
                return

            self.root.mkdir(parents=True, exist_ok=True)
            try:
                with open(self.lock_path, "a+b") as handle:
                    lock_handle(handle)
                    self._guard_state.depth = 1
                    try:
                        yield
                    finally:
                        self._guard_state.depth = 0
                        unlock_handle(handle)
            except OSError as error:
                raise IdentityStoreError(
                    f"Could not lock {self.path.name}: {error}"
                ) from error

    def _load_migrations(self):
        if not self.migration_path.exists():
            return {}
        payload = self._read_json(self.migration_path)
        if not isinstance(payload, dict):
            raise IdentityStoreError(
                f"{self.migration_path.name} is invalid; refusing to repeat migration."
            )
        return payload

    @staticmethod
    def _read_json(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                return json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise IdentityStoreError(f"Could not read {path.name}: {error}") from error

    @staticmethod
    def _copy_missing_tree(source, target):
        copied = []
        for item in source.rglob("*"):
            relative = item.relative_to(source)
            destination = target / relative
            if item.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            elif item.is_file() and not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, destination)
                copied.append(relative)
        return copied

    @staticmethod
    def _atomic_json_write(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(
            f"{path.suffix}.{os.getpid()}.{threading.get_ident()}."
            f"{uuid.uuid4().hex[:8]}.tmp"
        )
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp_path, path)
        except OSError as error:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise IdentityStoreError(f"Could not save {path.name}: {error}") from error


def timestamp():
    return datetime.now().isoformat(timespec="seconds")


def version_tuple(version):
    match = VERSION_PATTERN.fullmatch(str(version or "").strip())
    if not match:
        raise ValueError("Version must use numeric major.minor.patch format.")
    core = str(version).split("-", 1)[0].split("+", 1)[0]
    return tuple(int(part) for part in core.split("."))


def path_lock(path):
    key = str(Path(path).resolve())
    with _PATH_LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(key, threading.RLock())


def lock_handle(handle):
    if os.name == "nt":
        import msvcrt

        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def unlock_handle(handle):
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
