#!/usr/bin/env python3
"""Conan test package for ahoy 2.5.0."""
import io
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run


class AhoyTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["ahoy"].package_folder
        exe_name = "ahoy.exe" if str(self.settings.os) == "Windows" else "ahoy"
        ahoy = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(ahoy), f"ahoy binary not found: {ahoy}"

        with open(ahoy, "rb") as f:
            assert f.read(4) == b"\x7fELF", "ahoy is not an ELF binary"

        if not can_run(self):
            return

        buf = io.StringIO()
        rc = self.run(f'"{ahoy}" --version', env="conanrun", stdout=buf, stderr=buf, ignore_errors=True)
        out = buf.getvalue().strip()
        assert rc == 0, f"ahoy --version failed: {out}"
        assert "2.5.0" in out, f"ahoy --version missing 2.5.0: {out}"

        script = Path(self.source_folder) / "fixture_hello.sh"
        assert script.is_file(), f"missing ahoy fixture script: {script}"
        script.write_text(
            script.read_text(encoding="utf-8").replace("\r\n", "\n"),
            encoding="utf-8",
            newline="\n",
        )
        os.chmod(script, 0o755)

        work = Path(self.build_folder) / "fixture"
        work.mkdir(parents=True, exist_ok=True)
        config = work / ".ahoy.yml"
        script_for_yaml = str(script).replace("\\", "/")
        config.write_text(
            "ahoyapi: v2\n"
            "commands:\n"
            "  hello:\n"
            "    usage: print hello\n"
            f"    cmd: sh \"{script_for_yaml}\"\n",
            encoding="utf-8",
        )

        buf = io.StringIO()
        rc = self.run(
            f'"{ahoy}" -f "{config}" hello',
            cwd=str(work),
            env="conanrun",
            stdout=buf,
            stderr=buf,
            ignore_errors=True,
        )
        out = buf.getvalue()
        assert rc == 0, f"ahoy hello failed: {out}"
        assert "ahoy-package-ok" in out, f"ahoy command output mismatch: {out}"
