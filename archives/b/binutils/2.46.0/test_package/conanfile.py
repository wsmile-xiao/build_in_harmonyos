#!/usr/bin/env python3
"""Consumer test for the installed GNU Binutils command suite."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class BinutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["binutils"].package_folder
        bindir = os.path.join(package, "bin")
        tools = {
            name: os.path.join(bindir, name)
            for name in ("as", "ld", "ar", "nm", "objdump", "readelf", "strip")
        }
        missing = [path for path in tools.values() if not os.path.isfile(path)]
        if missing:
            raise RuntimeError("packaged binutils files missing: " + ", ".join(missing))

        shell = os.environ.get("CONFIG_SHELL")
        if not shell or not os.path.isfile(shell) or not os.access(shell, os.X_OK):
            shell = next(
                (
                    candidate
                    for candidate in (
                        shutil.which("bash"),
                        shutil.which("sh"),
                        "/data/service/hnp/bin/bash",
                        "/system/bin/sh",
                        "/bin/sh",
                    )
                    if candidate
                    and os.path.isfile(candidate)
                    and os.access(candidate, os.X_OK)
                ),
                None,
            )
        if not shell:
            raise RuntimeError(
                "No usable test shell: set CONFIG_SHELL or provide bash/sh"
            )
        script = os.path.join(self.source_folder, "test.sh")
        fixture_dir = self.source_folder
        output_dir = os.path.join(self.build_folder, "binutils-consumer-output")
        command = " ".join(
            shlex.quote(value)
            for value in (
                shell,
                script,
                fixture_dir,
                output_dir,
                tools["as"],
                tools["ld"],
                tools["ar"],
                tools["nm"],
                tools["objdump"],
                tools["readelf"],
                tools["strip"],
            )
        )
        self.run(command, env="conanrun")
        if str(self.settings.os) == "OHOS" and can_run(self) and not cross_building(self):
            compiler_map = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            compiler = compiler_map.get("c") or shutil.which("clang")
            if not compiler:
                raise RuntimeError("native OHOS consumer requires the C compiler")
            native_command = " ".join(shlex.quote(value) for value in (
                "python3", os.path.join(self.source_folder, "native-test.py"), package,
                os.path.join(self.build_folder, "binutils-native-output"), compiler))
            self.run(native_command, env="conanrun")
