import hashlib
import json
import os
import re
import threading
import uuid
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from commands.base import Command


BACKUP_SCHEMA = "astra-profile-backup/v1"
PERSISTENT_FILES = ("long_memory.json", "facts.json")
PERSISTENT_DIRS = (
    "actions",
    "automation",
    "experience",
    "learning",
    "self_learning",
)
MAX_BACKUP_BYTES = 128 * 1024 * 1024


class BackupCommand(Command):
    help_text = (
        "- backup create [label] - create a verified ZIP of the active profile\n"
        "- backup list - list local profile backups\n"
        "- backup verify <file|latest> - verify manifest, hashes, and ZIP integrity"
    )

    def __init__(
        self,
        config,
        memory,
        identity=None,
        profile_dir=None,
        logger=None,
        now_provider=None,
    ):
        super().__init__(logger)
        self.config = config
        self.memory = memory
        self.identity = identity
        self.profile_dir = self._profile_dir(profile_dir)
        self.backup_dir = self.profile_dir / "backups"
        self.now_provider = now_provider or datetime.now

    def handle(self, message, normalized):
        if normalized in {"backup", "backup create", "profile backup"}:
            return self._create_response("")
        if normalized.startswith("backup create "):
            label = message.strip()[len("backup create "):]
            return self._create_response(label)
        if normalized in {"backup list", "backups", "profile backups"}:
            return self._list_response()
        if normalized.startswith("backup verify "):
            target = message.strip()[len("backup verify "):]
            return self._verify_response(target)
        return None

    def create(self, label=""):
        safe_label = normalize_label(label)
        now = self.now_provider()
        actor = normalize_label(
            getattr(self.identity, "user_id", "") or self.profile_dir.name
        ) or "legacy"
        suffix = f"_{safe_label}" if safe_label else ""
        filename = (
            f"astra_backup_{actor}_{now.strftime('%Y%m%d_%H%M%S_%f')}"
            f"{suffix}.zip"
        )
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        destination = self.backup_dir / filename
        tmp_path = destination.with_suffix(
            f"{destination.suffix}.{os.getpid()}.{threading.get_ident()}."
            f"{uuid.uuid4().hex[:8]}.tmp"
        )
        sources = self._source_files()
        if not sources:
            raise FileNotFoundError(
                "No persistent profile data exists yet; use ASTRA before creating a backup."
            )
        expected_size = sum(source.stat().st_size for source in sources)
        if expected_size > MAX_BACKUP_BYTES:
            raise ValueError(
                "Profile data exceeds the 128 MiB safety limit for one backup."
            )

        records = []
        total_size = 0
        try:
            with zipfile.ZipFile(
                tmp_path,
                mode="x",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as archive:
                for source in sources:
                    relative = source.relative_to(self.profile_dir).as_posix()
                    record = write_hashed_file(archive, source, relative)
                    total_size += record["size"]
                    if total_size > MAX_BACKUP_BYTES:
                        raise ValueError(
                            "Profile data exceeds the 128 MiB safety limit for one backup."
                        )
                    records.append(record)
                manifest = {
                    "schema": BACKUP_SCHEMA,
                    "created": now.isoformat(timespec="seconds"),
                    "astra_version": str(getattr(self.config, "version", "unknown")),
                    "user_id": getattr(self.identity, "user_id", None),
                    "label": safe_label or None,
                    "file_count": len(records),
                    "total_bytes": total_size,
                    "files": records,
                }
                archive.writestr(
                    "manifest.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                )

            verification = verify_backup_path(tmp_path)
            if not verification["valid"]:
                raise ValueError(
                    "New backup failed verification: "
                    + "; ".join(verification["issues"])
                )
            os.replace(tmp_path, destination)
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        return {
            "path": destination,
            "files": len(records),
            "bytes": total_size,
            "sha256": sha256_file(destination),
        }

    def list_backups(self):
        if not self.backup_dir.exists():
            return []
        items = []
        for path in self.backup_dir.glob("astra_backup_*.zip"):
            if path.is_symlink():
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            items.append(
                {
                    "name": path.name,
                    "bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(
                        timespec="seconds"
                    ),
                }
            )
        return sorted(items, key=lambda item: item["modified"], reverse=True)

    def verify(self, target):
        path = self._resolve_backup(target)
        report = verify_backup_path(path)
        report["path"] = path
        return report

    def _create_response(self, label):
        try:
            report = self.create(label)
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            return f"Profile backup failed: {error}"
        return (
            f"Verified profile backup created: {report['path']}\n"
            f"- files: {report['files']}\n"
            f"- source bytes: {report['bytes']}\n"
            f"- SHA-256: {report['sha256']}\n"
            "Keep this ZIP private; it contains personal memory and learning data."
        )

    def _list_response(self):
        items = self.list_backups()
        if not items:
            return "No backups exist for the active profile."
        lines = ["Backups for the active profile:"]
        for item in items[:20]:
            lines.append(
                f"- {item['name']} ({item['bytes']} bytes, {item['modified']})"
            )
        return "\n".join(lines)

    def _verify_response(self, target):
        try:
            report = self.verify(target)
        except (FileNotFoundError, ValueError, OSError) as error:
            return f"Backup verification failed: {error}"
        if not report["valid"]:
            return (
                f"Backup is invalid: {report['path'].name}\n- "
                + "\n- ".join(report["issues"])
            )
        return (
            f"Backup verified: {report['path'].name}\n"
            f"- files: {report['files']}\n"
            f"- source bytes: {report['bytes']}"
        )

    def _profile_dir(self, explicit):
        if explicit is not None:
            return Path(explicit)
        identity_dir = getattr(self.identity, "data_dir", None)
        if identity_dir is not None:
            return Path(identity_dir)
        long_memory = getattr(self.memory, "long_memory", None)
        memory_path = getattr(long_memory, "path", None)
        if memory_path is None:
            raise ValueError("Could not determine the active profile data directory.")
        return Path(memory_path).parent

    def _source_files(self):
        sources = []
        for filename in PERSISTENT_FILES:
            path = self.profile_dir / filename
            if path.is_file() and not path.is_symlink():
                sources.append(path)
        for dirname in PERSISTENT_DIRS:
            root = self.profile_dir / dirname
            if not root.is_dir() or root.is_symlink():
                continue
            for path in root.rglob("*"):
                if (
                    path.is_file()
                    and not path.is_symlink()
                    and ".tmp" not in path.name
                ):
                    sources.append(path)
        return sorted(set(sources), key=lambda path: path.as_posix())

    def _resolve_backup(self, target):
        value = str(target or "").strip()
        if not value:
            raise ValueError("Use: backup verify <file|latest>")
        items = self.list_backups()
        if value.casefold() == "latest":
            if not items:
                raise FileNotFoundError("No backups exist for the active profile.")
            return self.backup_dir / items[0]["name"]
        if Path(value).name != value or "/" in value or "\\" in value:
            raise ValueError("Backup verification accepts a filename, not a path.")
        exact = self.backup_dir / value
        if exact.is_file() and not exact.is_symlink():
            return exact
        matches = [item for item in items if item["name"].startswith(value)]
        if len(matches) == 1:
            return self.backup_dir / matches[0]["name"]
        if len(matches) > 1:
            raise ValueError(f"Backup name is ambiguous: {value}")
        raise FileNotFoundError(f"Backup not found: {value}")


def write_hashed_file(archive, source, archive_name):
    digest = hashlib.sha256()
    size = 0
    with open(source, "rb") as input_handle:
        with archive.open(archive_name, mode="w", force_zip64=True) as output_handle:
            while True:
                chunk = input_handle.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
                output_handle.write(chunk)
    return {
        "path": archive_name,
        "size": size,
        "sha256": digest.hexdigest(),
    }


def verify_backup_path(path):
    backup_path = Path(path)
    issues = []
    file_count = 0
    total_bytes = 0
    try:
        with zipfile.ZipFile(backup_path, "r") as archive:
            names = archive.namelist()
            unsafe = [name for name in names if not safe_archive_name(name)]
            if unsafe:
                issues.append("Archive contains an unsafe path.")
            file_infos = [
                info
                for info in archive.infolist()
                if not info.is_dir() and info.filename != "manifest.json"
            ]
            if sum(info.file_size for info in file_infos) > MAX_BACKUP_BYTES:
                issues.append("Archive exceeds the 128 MiB verification safety limit.")
                return verification_report(False, 0, 0, issues)
            if names.count("manifest.json") != 1:
                issues.append("Archive must contain exactly one manifest.json.")
                return verification_report(False, 0, 0, issues)
            try:
                manifest = json.loads(archive.read("manifest.json"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                issues.append(f"Manifest is invalid: {error}")
                return verification_report(False, 0, 0, issues)
            if not isinstance(manifest, dict) or manifest.get("schema") != BACKUP_SCHEMA:
                issues.append("Manifest schema is unsupported.")
                return verification_report(False, 0, 0, issues)
            records = manifest.get("files")
            if not isinstance(records, list) or not all(
                isinstance(item, dict) for item in records
            ):
                issues.append("Manifest file list is invalid.")
                return verification_report(False, 0, 0, issues)

            expected_names = {str(item.get("path", "")) for item in records}
            actual_list = [name for name in names if name != "manifest.json"]
            actual_names = set(actual_list)
            if expected_names != actual_names:
                issues.append("Manifest file list does not match archive contents.")
            if len(expected_names) != len(records):
                issues.append("Manifest contains duplicate file paths.")
            if len(actual_names) != len(actual_list):
                issues.append("Archive contains duplicate file paths.")

            for record in records:
                name = str(record.get("path", ""))
                if not safe_archive_name(name) or name not in actual_names:
                    continue
                digest = hashlib.sha256()
                size = 0
                with archive.open(name, "r") as handle:
                    while True:
                        chunk = handle.read(1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        digest.update(chunk)
                file_count += 1
                total_bytes += size
                if size != record.get("size"):
                    issues.append(f"Size mismatch: {name}")
                if digest.hexdigest() != record.get("sha256"):
                    issues.append(f"SHA-256 mismatch: {name}")
            if manifest.get("file_count") != file_count:
                issues.append("Manifest file_count does not match verified files.")
            if manifest.get("total_bytes") != total_bytes:
                issues.append("Manifest total_bytes does not match verified files.")
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        issues.append(f"ZIP could not be read: {error}")
    return verification_report(not issues, file_count, total_bytes, issues)


def verification_report(valid, files, size, issues):
    return {
        "valid": bool(valid),
        "files": int(files),
        "bytes": int(size),
        "issues": list(issues),
    }


def safe_archive_name(value):
    text = str(value or "")
    if not text or "\\" in text or ":" in text:
        return False
    path = PurePosixPath(text)
    return not path.is_absolute() and ".." not in path.parts


def normalize_label(value):
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip())
    return normalized.strip("-_")[:40]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
