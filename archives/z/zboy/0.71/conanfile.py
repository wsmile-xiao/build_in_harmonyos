#!/usr/bin/env python3
"""Conan recipe for zBoy 0.71, a SDL2-based Game Boy emulator."""

import os
import shutil
import sys
import tempfile

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class ZboyConan(ConanFile):
    name = "zboy"
    version = "0.71"
    description = "SDL2-based Game Boy emulator"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/zboy/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualBuildEnv"
    exports_sources = "patches/*", "test_package/run_upstream_rom_tests.py"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")

    def layout(self):
        basic_layout(self)
        self.folders.source = "."

    def source(self):
        # SourceForge's stable download endpoint ends in `/download`, so
        # Conan cannot infer the archive type from the URL. Keep the original
        # .tar.xz suffix when fetching so get() selects its tar.xz extractor.
        get(
            self,
            **self.conan_data["sources"],
            filename="zboy-0.71.tar.xz",
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsToolchain supplies the Conan-selected compiler and flags to
        # the upstream Makefile, even though zBoy has no configure script.
        AutotoolsToolchain(self).generate()

    def build(self):
        self.run("make -f Makefile.linux -j1", cwd=self.source_folder, env="conanbuild")

        if str(self.settings.os) != "OHOS":
            self.output.info(
                "Upstream ROM suites are run on the native OHOS/armv8 profile."
            )
            return
        if not can_run(self):
            self.output.warning(
                "Skipping upstream ROM runtime checks on this cross-build host; "
                "run conan create with the native OHOS/armv8 profile."
            )
            return

        # Keep the diagnostic copy outside Conan's build/source tree. With the
        # basic layout used here, those folders can resolve to the same path;
        # placing a copy below either one would recursively copy itself.
        with tempfile.TemporaryDirectory(prefix="zboy-rom-tests-") as test_source:
            shutil.copytree(self.source_folder, test_source, dirs_exist_ok=True)
            self.run(
                "make -f Makefile.linux clean",
                cwd=test_source,
                env="conanbuild",
            )
            self.run(
                'make -f Makefile.linux -j1 CFLAGS="$CFLAGS -DDEBUGSERIAL"',
                cwd=test_source,
                env="conanbuild",
            )

            test_binary = os.path.join(test_source, "zboy")
            self._sign_test_binary(test_binary)
            rom_root = os.path.join(test_source, "tools", "roms")
            runner = os.path.join(
                self.export_sources_folder, "test_package", "run_upstream_rom_tests.py"
            )
            log_path = os.path.join(self.build_folder, "upstream-rom-tests.log")
            self.run(
                '"{}" "{}" --binary "{}" --rom-root "{}" --timeout 900 --log "{}"'.format(
                    sys.executable, runner, test_binary, rom_root, log_path
                ),
                cwd=test_source,
                env="conanrun",
            )

    def _sign_test_binary(self, path):
        """Sign the temporary OHOS-only ROM test executable for device execution."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise RuntimeError("HarmonyOS binary-sign-tool is required for upstream ROM tests")
        if os.path.isfile(objcopy):
            self.run(
                '"{}" --remove-section .codesign "{}"'.format(objcopy, path),
                ignore_errors=True,
            )
        signed = path + ".signed"
        self.run(
            '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                signer, path, signed
            )
        )
        if not os.path.isfile(signed):
            raise RuntimeError("HarmonyOS signer did not produce the ROM test executable")
        shutil.move(signed, path)
        os.chmod(path, 0o755)

    def package(self):
        binary = "zboy.exe" if str(self.settings.os) == "Windows" else "zboy"
        copy(self, binary, src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(
            self,
            "license.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "zboy.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "zboy"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
