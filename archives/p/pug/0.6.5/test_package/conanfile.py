#!/usr/bin/env python3
"""Conan test package for pug 0.6.5."""
import io
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run


class PugTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["pug"].package_folder
        exe_name = "pug.exe" if str(self.settings.os) == "Windows" else "pug"
        pug = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(pug), f"pug binary not found: {pug}"

        with open(pug, "rb") as f:
            assert f.read(4) == b"\x7fELF", "pug is not an ELF binary"

        if not can_run(self):
            return

        script = Path(self.source_folder) / "version_smoke.sh"
        assert script.is_file(), f"missing pug smoke script: {script}"
        script.write_text(
            script.read_text(encoding="utf-8").replace("\r\n", "\n"),
            encoding="utf-8",
            newline="\n",
        )
        os.chmod(script, 0o755)

        buf = io.StringIO()
        rc = self.run(
            f'sh "{script}" "{pug}" "0.6.5"',
            env="conanrun",
            stdout=buf,
            stderr=buf,
            ignore_errors=True,
        )
        out = buf.getvalue().strip()
        assert rc == 0, f"pug version smoke failed: {out}"
        assert "0.6.5" in out, f"pug --version missing 0.6.5: {out}"
