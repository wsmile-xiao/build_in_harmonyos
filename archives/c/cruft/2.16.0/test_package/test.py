#!/usr/bin/env python3
"""Functional test for cruft 2.16.0 – exercises create / check / diff.

Creates a minimal local Git-backed Cookiecutter template, generates a
project from it with ``cruft.create``, verifies the project is in-sync
with ``cruft.check``, then modifies the project and confirms
``cruft.diff`` detects the change.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import cruft


def run_git(*args, cwd):
    """Run a git command, raising on failure."""
    subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True
    )


def main():
    if subprocess.run(
        ["git", "--version"], capture_output=True
    ).returncode != 0:
        raise RuntimeError("git is required by cruft")

    # HarmonyOS application storage can report a virtual owner to Git.
    # Keep the safe-directory override local to this test process.
    config_index = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    os.environ["GIT_CONFIG_COUNT"] = str(config_index + 1)
    os.environ[f"GIT_CONFIG_KEY_{config_index}"] = "safe.directory"
    os.environ[f"GIT_CONFIG_VALUE_{config_index}"] = "*"

    with tempfile.TemporaryDirectory(prefix="cruft-test-") as tmp:
        root = Path(tmp)
        template = root / "template"
        project_template = template / "{{cookiecutter.project_name}}"
        project_template.mkdir(parents=True)
        (template / "cookiecutter.json").write_text(
            '{"project_name": "demo"}\n', encoding="utf-8"
        )
        (project_template / "README.md").write_text(
            "# {{cookiecutter.project_name}}\n", encoding="utf-8"
        )

        run_git("init", cwd=template)
        run_git("config", "user.name", "Conan Test", cwd=template)
        run_git(
            "config", "user.email", "conan-test@example.invalid", cwd=template
        )
        run_git("add", ".", cwd=template)
        run_git("commit", "-m", "Initial template", cwd=template)

        # cruft.create generates a project from the template
        project = cruft.create(template.as_posix(), root / "output")

        # cruft.check returns True when the project is in sync
        if not cruft.check(project):
            raise AssertionError(
                "freshly generated project is unexpectedly stale"
            )

        # Modify the project and verify cruft.diff detects the change
        readme = project / "README.md"
        readme.write_text("# modified\n", encoding="utf-8")

        # With exit_code=True, cruft.diff returns False when changes exist
        if cruft.diff(project, exit_code=True):
            raise AssertionError(
                "cruft.diff did not detect the local change"
            )

    print(f"cruft {cruft.__version__}: create/check/diff passed")


if __name__ == "__main__":
    main()
