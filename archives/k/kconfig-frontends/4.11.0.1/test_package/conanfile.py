#!/usr/bin/env python3
"""Consumer tests for the kconfig parser and text frontends."""

import os
import shlex
import shutil
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class KconfigFrontendsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("cross-build: parser and frontend consumer tests skipped")
            return

        package = self.dependencies[self.tested_reference_str]
        parser_test = Path(self.build_folder) / "kconfig_parser_consumer"
        if not parser_test.is_file():
            raise AssertionError(f"CMake did not build parser consumer: {parser_test}")
        kconfig = Path(self.source_folder) / "fixtures" / "Kconfig"

        if self.settings.os == "OHOS":
            home = Path(os.path.expanduser("~"))
            if not home.is_absolute() or str(home) == ".":
                raise ConanInvalidConfiguration("OHOS test requires an absolute HOME directory")
            home_real = home.resolve()
            try:
                home_real.relative_to(Path("/storage/Users"))
            except ValueError as error:
                raise ConanInvalidConfiguration(
                    "OHOS HMDFS test requires HOME to resolve below /storage/Users"
                ) from error
            workdir = home / "tmp" / "kconfig-frontends-4.11.0.1-test"
        else:
            workdir = Path(self.build_folder) / "kconfig-frontends-test"

        workdir.mkdir(parents=True, exist_ok=True)
        test_kconfig = workdir / "Kconfig"
        shutil.copyfile(kconfig, test_kconfig)
        config = workdir / ".config"
        # This HarmonyOS work directory persists across Conan invocations.
        # Start the defaults check from a clean state; later checks in this
        # same run verify that an explicitly saved value survives olddefconfig.
        config.unlink(missing_ok=True)
        os.environ["KCONFIG_CONFIG"] = str(config)
        os.environ["TERM"] = "xterm-256color"

        binaries = {
            name: Path(package.package_folder) / package.cpp_info.bindirs[0] / name
            for name in ("kconfig-conf", "kconfig-mconf", "kconfig-nconf")
        }
        for name, binary in binaries.items():
            if not binary.is_file():
                raise AssertionError(f"package is missing {name}: {binary}")

        self.run(
            f"{shlex.quote(str(binaries['kconfig-conf']))} --olddefconfig "
            f"{shlex.quote(str(test_kconfig))}",
            cwd=str(workdir),
            env="conanrun",
        )
        generated = config.read_text(encoding="utf-8")
        for expected in (
            "CONFIG_ENABLE_PARSER=y",
            "CONFIG_DEFAULT_COUNT=7",
            "CONFIG_DEFAULT_CHOICE_A=y",
            'CONFIG_DEFAULT_TEXT="HarmonyOS"',
        ):
            if expected not in generated:
                raise AssertionError(f"conf output is missing {expected!r}: {generated!r}")

        self.run(
            f"{shlex.quote(str(parser_test))} {shlex.quote(str(test_kconfig))}",
            cwd=str(workdir),
            env="conanrun",
        )
        generated = config.read_text(encoding="utf-8")
        if "# CONFIG_ENABLE_PARSER is not set" not in generated:
            raise AssertionError("parser API did not persist the changed symbol with conf_write()")

        # olddefconfig must preserve an existing user choice while resolving
        # the rest of the Kconfig tree from defaults.
        self.run(
            f"{shlex.quote(str(binaries['kconfig-conf']))} --olddefconfig "
            f"{shlex.quote(str(test_kconfig))}",
            cwd=str(workdir),
            env="conanrun",
        )
        generated = config.read_text(encoding="utf-8")
        if "# CONFIG_ENABLE_PARSER is not set" not in generated:
            raise AssertionError("conf --olddefconfig did not preserve the saved symbol value")

        frontend_runner = Path(self.source_folder) / "test_text_frontends.py"
        command = shlex.join(
            [
                sys.executable,
                str(frontend_runner),
                str(binaries["kconfig-mconf"]),
                str(binaries["kconfig-nconf"]),
                str(test_kconfig),
            ]
        )
        self.run(command, cwd=str(workdir), env="conanrun")

        if self.settings.os == "OHOS":
            try:
                config.resolve().relative_to(home_real / "tmp")
            except ValueError as error:
                raise AssertionError(
                    "HarmonyOS config output did not resolve below the HMDFS-backed HOME/tmp path"
                ) from error
            if not config.is_file() or "CONFIG_DEFAULT_COUNT=7" not in config.read_text(encoding="utf-8"):
                raise AssertionError("HarmonyOS HMDFS config read/write check failed")
            self.output.info(f"HarmonyOS HMDFS config read/write verified at {config}")
