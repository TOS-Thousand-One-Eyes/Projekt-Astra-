import json
import urllib.request

REPO_URL = "https://github.com/TOS-Thousand-One-Eyes/Projekt-Astra-"
VERSION_URL = "https://raw.githubusercontent.com/TOS-Thousand-One-Eyes/Projekt-Astra-/main/ASTRA/config.json"


class UpdateChecker:

    def __init__(self, current_version, logger, version_url=VERSION_URL, repo_url=REPO_URL, timeout=3, fetch=None):
        self.current_version = current_version
        self.logger = logger
        self.version_url = version_url
        self.repo_url = repo_url
        self.timeout = timeout
        self.fetch = fetch or self._fetch_from_url

    def _fetch_from_url(self):
        with urllib.request.urlopen(self.version_url, timeout=self.timeout) as response:
            return json.load(response)["version"]

    def check(self):
        try:
            current_parsed = self._parse(self.current_version)
        except Exception:
            self.logger.warning(
                "Local version is unknown (check config.json's \"version\" key); "
                "skipping the up-to-date comparison."
            )
            self._report_latest_without_comparison()
            return

        try:
            latest = self.fetch()
            latest_parsed = self._parse(latest)
        except Exception as error:
            self.logger.debug(f"Update check failed: {error}")
            return

        if latest_parsed > current_parsed:
            self.logger.info(
                f"A newer version of Astra (v{latest}) is available. Download it at {self.repo_url}"
            )
        else:
            self.logger.info("Astra is up to date.")

    def _report_latest_without_comparison(self):
        try:
            latest = self.fetch()
        except Exception as error:
            self.logger.debug(f"Update check failed: {error}")
            return
        self.logger.info(f"Latest available version: v{latest}. Download it at {self.repo_url}")

    @staticmethod
    def _parse(version):
        return tuple(int(part) for part in version.split("."))
