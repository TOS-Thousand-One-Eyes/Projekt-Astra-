import json
import urllib.request

REPO_URL = "https://github.com/TOS-Thousand-One-Eyes/Projekt-Astra-"
VERSION_URL = "https://raw.githubusercontent.com/TOS-Thousand-One-Eyes/Projekt-Astra-/main/ASTRA/config.json"


class UpdateChecker:

    def __init__(self, current_version, version_url=VERSION_URL, repo_url=REPO_URL, timeout=3, fetch=None):
        self.current_version = current_version
        self.version_url = version_url
        self.repo_url = repo_url
        self.timeout = timeout
        self.fetch = fetch or self._fetch_from_url

    def _fetch_from_url(self):
        with urllib.request.urlopen(self.version_url, timeout=self.timeout) as response:
            return json.load(response)["version"]

    def check(self):
        try:
            latest = self.fetch()
            latest_parsed = self._parse(latest)
            current_parsed = self._parse(self.current_version)
        except Exception:
            return None

        if latest_parsed > current_parsed:
            return f"A newer version of Astra (v{latest}) is available. Download it at {self.repo_url}"
        return None

    @staticmethod
    def _parse(version):
        return tuple(int(part) for part in version.split("."))
