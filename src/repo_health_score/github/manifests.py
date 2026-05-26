"""
Package manager manifest detection.
Auto-detects what package managers a repo uses.
"""

import os
from dataclasses import dataclass


DETECTORS = {
    "npm": {
        "files": ["package.json"],
        "lock_file": "package-lock.json",
    },
    "pip": {
        "files": ["requirements.txt", "setup.py", "pyproject.toml"],
        "lock_file": None,
    },
    "poetry": {
        "files": ["pyproject.toml"],
        "lock_file": "poetry.lock",
    },
    "go": {
        "files": ["go.mod"],
        "lock_file": "go.sum",
    },
    "cargo": {
        "files": ["Cargo.toml"],
        "lock_file": "Cargo.lock",
    },
    "maven": {
        "files": ["pom.xml"],
        "lock_file": None,
    },
    "gradle": {
        "files": ["build.gradle", "settings.gradle"],
        "lock_file": None,
    },
    "gem": {
        "files": ["Gemfile"],
        "lock_file": "Gemfile.lock",
    },
    "nuget": {
        "files": ["*.csproj", "*.nuspec"],
        "lock_file": None,
    },
    "pubspec": {
        "files": ["pubspec.yaml"],
        "lock_file": "pubspec.lock",
    },
    "mix": {
        "files": ["mix.exs"],
        "lock_file": "mix.lock",
    },
    "yarn": {
        "files": ["package.json"],
        "lock_file": "yarn.lock",
    },
    "pnpm": {
        "files": ["package.json"],
        "lock_file": "pnpm-lock.yaml",
    },
}


@dataclass
class PackageManifest:
    package_manager: str
    manifest_file: str
    has_lock_file: bool

    @classmethod
    def detect(cls, repo_path: str, default_branch: str = "main") -> list["PackageManifest"]:
        """
        Detect package managers from a repo.
        Takes repo path (owner/repo format for API) and default branch name.
        Returns list of detected PackageManifest objects.
        """
        # Import here to avoid circular dependency
        from .client import GitHubClient

        owner, repo = repo_path.split("/")
        client = GitHubClient.from_pat(os.getenv("GITHUB_TOKEN", ""))

        detected = []
        checked_manifests = set()

        for pm_name, config in DETECTORS.items():
            manifest_files = config["files"]
            lock_file = config.get("lock_file")

            for manifest in manifest_files:
                if manifest in checked_manifests:
                    continue
                checked_manifests.add(manifest)

                contents = client.get_contents(owner, repo, manifest)
                if contents is not None:
                    has_lock = False
                    if lock_file:
                        lock_contents = client.get_contents(owner, repo, lock_file)
                        has_lock = lock_contents is not None

                    detected.append(
                        PackageManifest(
                            package_manager=pm_name,
                            manifest_file=manifest,
                            has_lock_file=has_lock,
                        )
                    )
                    break

        return detected
