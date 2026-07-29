#!/usr/bin/env python3
"""Conan recipe for Opus 1.4."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class OpusConan(ConanFile):
    name = "opus"
    version = "1.4"
    description = "Low-latency interactive audio codec"
    license = "BSD-3-Clause"
    homepage = "https://opus-codec.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _component_tests = (
        "celt/tests/test_unit_types",
        "celt/tests/test_unit_mathops",
        "celt/tests/test_unit_entropy",
        "celt/tests/test_unit_laplace",
        "celt/tests/test_unit_dft",
        "celt/tests/test_unit_mdct",
        "celt/tests/test_unit_rotation",
        "celt/tests/test_unit_cwrs32",
        "silk/tests/test_unit_LPC_inv_pred_gain",
    )
    _integration_tests = (
        "tests/test_opus_api",
        "tests/test_opus_decode",
        "tests/test_opus_encode",
        "tests/test_opus_padding",
        "tests/test_opus_projection",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".opus-signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", output,
                        "-selfSign", "1"], check=True, timeout=60)
        sections = subprocess.run([readelf, "-SW", output], check=True,
                                  capture_output=True, text=True, timeout=30).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o555)
        os.replace(output, path)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["tests"] = "enabled"
        tc.project_options["docs"] = "disabled"
        tc.project_options["extra-programs"] = "disabled"

        if str(self.settings.os) == "OHOS":
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = executables.get("c", "")
            tool_dir = os.path.dirname(compiler)
            archive_tools = {
                "ar": executables.get("ar")
                or os.path.join(tool_dir, "llvm-ar"),
                "ranlib": executables.get("ranlib")
                or os.path.join(tool_dir, "llvm-ranlib"),
            }
            missing = [
                name for name, path in archive_tools.items()
                if not path or not os.path.isfile(path)
            ]
            if missing:
                raise ConanException(
                    "Required OHOS archive tools are missing: "
                    + ", ".join(missing)
                )
            tc.ar = archive_tools["ar"]
            tc.binaries["ranlib"] = archive_tools["ranlib"]

        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        if can_run(self):
            suffix = ".exe" if self.settings.os == "Windows" else ""
            for relative in self._component_tests + self._integration_tests:
                executable = os.path.join(self.build_folder, relative + suffix)
                if str(self.settings.os) == "OHOS":
                    self._sign_ohos_elf(executable)
                self.run(f'"{executable}"')

    def package(self):
        Meson(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared and can_run(self):
            self._sign_ohos_elf(os.path.join(self.package_folder, "lib", "libopus.so"))

    def package_info(self):
        self.cpp_info.libs = ["opus"]
        self.cpp_info.set_property("cmake_file_name", "Opus")
        self.cpp_info.set_property("cmake_target_name", "Opus::opus")
        self.cpp_info.set_property("pkg_config_name", "opus")
