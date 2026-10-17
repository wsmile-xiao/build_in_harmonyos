#!/usr/bin/env python3
"""Consumer test for qtwayland on HarmonyOS PC."""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtwaylandTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        pkg = self.dependencies["qtwayland"].package_folder
        # Qt6Config lives in the qtbase package; the qtwayland package
        # provides Qt6WaylandClientFeaturesPrivate cmake config files.
        # Both CMAKE_PREFIX_PATH and QT_ADDITIONAL_PACKAGES_PREFIX_PATH
        # are needed: the former for find_package(Qt6WaylandClientFeaturesPrivate),
        # the latter for Qt6's find_package(Qt6 COMPONENTS WaylandClient).
        tc.cache_variables["CMAKE_PREFIX_PATH"] = f"{qtbase_pkg};{pkg}"
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = pkg
        tc.generate()

        from conan.tools.env import Environment
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(pkg, "lib"))
        wayland_pkg = self.dependencies["wayland"].package_folder
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(wayland_pkg, "lib"))
        envvars = env.vars(self)
        envvars.save_script("test_qtwayland_env")

    def build(self):
        # Patch conanbuild.sh to prepend OHOS SDK lib path (same issue as
        # the main recipe: lld needs libxml2.so.16 from the SDK)
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        conanbuild_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.isfile(conanbuild_sh):
            with open(conanbuild_sh, "r", encoding="utf-8") as f:
                content = f.read()
            fixup = (
                f'\n# Fix: ensure OHOS SDK libxml2.so.16 is found first by lld\n'
                f'export LD_LIBRARY_PATH="{sdk_lib}'
                f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"\n'
            )
            if "OHOS SDK libxml2" not in content:
                with open(conanbuild_sh, "a", encoding="utf-8") as f:
                    f.write(fixup)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self) and str(self.settings.os) == "OHOS":
            for binary in self._test_binaries():
                self._sign(binary)

    def _test_binaries(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanInvalidConfiguration(
                "qtwayland test package has no build bindir"
            )
        return [os.path.join(bindirs[0], "test_qtwayland")]

    def _sign(self, path):
        """Self-sign the test binary so the OHOS loader permits execution."""
        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; it is required to run OHOS ELF binaries"
            )
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    unsigned,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            os.replace(signed, path)
            os.chmod(path, original_mode)

    def test(self):
        if can_run(self) and str(self.settings.os) == "OHOS":
            qtbase_pkg = self.dependencies["qtbase"].package_folder
            pkg = self.dependencies["qtwayland"].package_folder
            wayland_pkg = self.dependencies["wayland"].package_folder
            sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            libcxx_lib = os.path.join(sdk_lib, "aarch64-linux-ohos")
            ld_path = (
                libcxx_lib
                + ":" + os.path.join(qtbase_pkg, "lib")
                + ":" + os.path.join(pkg, "lib")
                + ":" + os.path.join(wayland_pkg, "lib")
                + ":" + sdk_lib
            )
            os.environ["LD_LIBRARY_PATH"] = (
                ld_path + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            )
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            os.environ["QT_PLUGIN_PATH"] = os.path.join(qtbase_pkg, "plugins")
            bindir = self.cpp.build.bindirs[0]
            self.run(os.path.join(bindir, "test_qtwayland"), env="conanrun")
