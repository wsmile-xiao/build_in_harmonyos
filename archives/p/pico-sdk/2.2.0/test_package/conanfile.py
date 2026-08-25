#!/usr/bin/env python3
"""Conan test_package for pico-sdk 2.2.0."""
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import load
from conan.tools.layout import basic_layout


class PicoSdkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        os.makedirs(self.build_folder, exist_ok=True)

        dep = self.dependencies["pico-sdk"]
        sdk_path = os.path.join(dep.package_folder, "share", "pico-sdk")
        version_file = os.path.join(sdk_path, "pico_sdk_version.cmake")
        if not os.path.isfile(version_file):
            raise ConanException("pico_sdk_version.cmake is missing from packaged SDK")

        version_content = load(self, version_file)
        for expected in (
            "set(PICO_SDK_VERSION_MAJOR 2)",
            "set(PICO_SDK_VERSION_MINOR 2)",
            "set(PICO_SDK_VERSION_REVISION 0)",
        ):
            if expected not in version_content:
                raise ConanException(f"Missing expected SDK version marker: {expected}")

        env_probe = (
            "import os, pathlib; "
            "sdk=os.environ.get('PICO_SDK_PATH'); "
            "assert sdk, 'PICO_SDK_PATH missing'; "
            "assert pathlib.Path(sdk, 'pico_sdk_version.cmake').is_file(), sdk"
        )
        self._run_tool([sys.executable, "-c", env_probe])

        pioasm_name = "pioasm.exe" if str(self.settings.os) == "Windows" else "pioasm"
        pioasm_path = os.path.join(dep.package_folder, "bin", pioasm_name)
        if not os.path.isfile(pioasm_path):
            raise ConanException(f"pioasm executable is missing from package: {pioasm_path}")

        smoke_script = os.path.join(self.source_folder, "smoke.py")
        smoke_pio = os.path.join(self.source_folder, "conandata_smoke.pio")
        smoke_header = os.path.join(self.build_folder, "conandata_smoke.pio.h")
        self._run_tool([sys.executable, smoke_script, pioasm_path, smoke_pio, smoke_header])

    def _quote(self, value):
        if str(self.settings.os) == "Windows":
            return f'"{value}"'
        return shlex.quote(value)

    def _run_tool(self, args):
        command = " ".join(self._quote(arg) for arg in args)
        if str(self.settings.os) == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f"{self._quote(bash)} -lc {self._quote(command)}", env="conanrun")
        else:
            self.run(command, env="conanrun")
