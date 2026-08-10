#!/usr/bin/env python3
"""Consumer test for qtshadertools on HarmonyOS PC."""

import os
import shutil
import stat
import subprocess
import tempfile
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block


class QtshadertoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        pkg = self.dependencies["qtshadertools"].package_folder
        # Qt6Config lives in the qtbase package; Qt6ShaderToolsConfig lives in
        # the qtshadertools package. Qt only searches the additional prefixes
        # listed in QT_ADDITIONAL_PACKAGES_PREFIX_PATH for module configs.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_pkg
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = pkg

        # Qt 6.5+ keeps RHI headers (QShader/QShaderBaker/...) only in the
        # versioned per-module include directories, which the Qt6 targets do
        # not expose on their INTERFACE_INCLUDE_DIRECTORIES. Inject them so the
        # <rhi/...> includes used by the test compile against the real headers.
        class RhiIncludeBlock(Block):
            template = textwrap.dedent(
                """\
                include_directories(BEFORE "{{ qtbase_rhi_inc }}" "{{ shadertools_rhi_inc }}")
                """
            )

            def context(self):
                return {
                    "qtbase_rhi_inc": os.path.join(
                        qtbase_pkg, "include", "QtGui", "6.11.1", "QtGui"
                    ),
                    "shadertools_rhi_inc": os.path.join(
                        pkg, "include", "QtShaderTools", "6.11.1", "QtShaderTools"
                    ),
                }

        tc.blocks["rhi_include"] = RhiIncludeBlock
        tc.generate()

    def build(self):
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
                "qtshadertools test package has no build bindir"
            )
        return [os.path.join(bindirs[0], "test_qtshadertools")]

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
        if not can_run(self):
            self.output.info("Skipping execution: cross-build without an emulator")
            return

        pkg = self.dependencies["qtshadertools"]
        executable = os.path.join(self.cpp.build.bindirs[0], "test_qtshadertools")
        self.run(executable, env="conanrun", ignore_errors=False)

        # Exercise the packaged qsb command-line tool (R34: call the package API).
        qsb = os.path.join(pkg.package_folder, "bin", "qsb")
        if not os.path.isfile(qsb):
            raise ConanInvalidConfiguration(f"qsb not found at {qsb}")

        self.run(f'"{qsb}" --version', env="conanrun", ignore_errors=False)

        shader_source = os.path.join(self.source_folder, "test.frag")
        qsb_output = os.path.join(self.build_folder, "test.qsb")
        self.run(
            f'"{qsb}" -o "{qsb_output}" "{shader_source}"',
            env="conanrun",
            ignore_errors=False,
        )
        if not os.path.isfile(qsb_output):
            raise ConanInvalidConfiguration("qsb did not produce a .qsb file")
        self.output.info("qsb shader bake produced a valid .qsb file")
