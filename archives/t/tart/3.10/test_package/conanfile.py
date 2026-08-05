#!/usr/bin/env python3
"""Conan test_package for tart 3.10."""

import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run


class TartTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Skipping runtime tests while cross-compiling")
            return

        tart = Path(self.dependencies["tart"].package_folder) / "bin" / "tart"
        work_dir = Path.cwd() / "tart-functional-test"
        signature = work_dir / "signature.out"
        custom = work_dir / "tart-custom"
        dates = work_dir / "tartdates"
        tags = work_dir / "tart.tags"
        config = work_dir / ".tartrc"

        shutil.rmtree(work_dir, ignore_errors=True)
        work_dir.mkdir(parents=True)

        try:
            smoke = Path(self.source_folder) / "smoke.sh"
            self.run(f'sh "{smoke}" "{tart}"', env="conanrun")

            custom.write_text("%c1\n%vi\n%c2\n", encoding="utf-8")
            dates.write_text("01/01:HarmonyOS special date smoke test\n", encoding="utf-8")
            tags.write_text("HarmonyOS tart smoke test tagline\n", encoding="utf-8")
            config.write_text(
                "\n".join([
                    "CustomText1=LinuxTaRT test header",
                    "CustomText2=LinuxTaRT test footer",
                    f"SignatureFile={signature}",
                    f"TagLineDatabase={tags}",
                    f"SpecialDates={dates}",
                    f"CustomFile={custom}",
                    "ShowDate=0",
                    "RunQuiet=1",
                    "ShowVersion=1",
                    "CenterText=0",
                    "UseCustomText=1",
                    "UseSpecialDates=0",
                    "RunAsDaemon=0",
                    "",
                ]),
                encoding="utf-8",
            )

            self.run(f'"{tart}" --config "{config}" +cust +q -sd', env="conanrun")
            content = signature.read_text(encoding="utf-8")
            for expected in [
                "LinuxTaRT test header",
                "3.10",
                "LinuxTaRT test footer",
            ]:
                if expected not in content:
                    raise RuntimeError(f"Generated signature is missing: {expected}")
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
