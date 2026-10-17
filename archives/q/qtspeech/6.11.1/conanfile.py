#!/usr/bin/env python3
"""Conan recipe for Qt Speech 6.11.1 on HarmonyOS PC."""

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
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    unzip,
)


class QtSpeechConan(ConanFile):
    name = "qtspeech"
    version = "6.11.1"
    description = "Qt APIs for text-to-speech accessibility"
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qttexttospeech-index.html"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    _upstream_test_targets = ("tst_qtexttospeech", "tst_qvoice")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "qtbase/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "qtmultimedia/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtspeech/6.11.1 is a HarmonyOS PC adaptation"
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "qtspeech/6.11.1 supports HarmonyOS PC aarch64 only"
            )
        if str(self.settings.compiler) != "clang":
            raise ConanInvalidConfiguration(
                "qtspeech/6.11.1 requires the HarmonyOS clang toolchain"
            )
        if self.settings_build.os != "OHOS" or str(self.settings_build.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "qtspeech/6.11.1 requires a native HarmonyOS PC aarch64 build context"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        source = self.conan_data["sources"]
        urls = source["url"]
        if isinstance(urls, str):
            urls = [urls]
        local_url = next((url for url in urls if url.startswith("file://")), None)
        if local_url:
            # W3 pre-download preserves literal %2D in its cache filename, while
            # Conan's file URL handler percent-decodes it before opening.
            archive = local_url[len("file://"):]
            if not os.path.isfile(archive):
                decoded = archive.replace("%2D", "-").replace("%2d", "-")
                if os.path.isfile(decoded):
                    archive = decoded
            check_sha256(self, archive, source["sha256"])
            unzip(self, archive, destination=self.source_folder, strip_root=True)
            return
        get(self, **source, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        class OhosLinuxPlatformBlock(Block):
            template = textwrap.dedent(
                """\
                # HarmonyOS PC executes the produced aarch64 binaries locally.
                # Use Linux platform rules for SONAME handling without cross mode;
                # the OHOS clang driver still targets aarch64-unknown-linux-ohos.
                set(CMAKE_SYSTEM_NAME Linux)
                set(CMAKE_HOST_SYSTEM_NAME Linux)
                set(CMAKE_CROSSCOMPILING FALSE)
                set(CMAKE_SYSTEM_PROCESSOR aarch64)
                set(CMAKE_HOST_SYSTEM_PROCESSOR aarch64)
                """
            )

            def context(self):
                return {}

        tc.blocks["user_toolchain"] = OhosLinuxPlatformBlock
        qtbase = self.dependencies["qtbase"].package_folder
        qtmultimedia = self.dependencies["qtmultimedia"].package_folder
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": f"{qtbase};{qtmultimedia}",
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH": qtmultimedia,
                "Qt6_DIR": os.path.join(qtbase, "lib", "cmake", "Qt6"),
                "Qt6Multimedia_DIR": os.path.join(
                    qtmultimedia, "lib", "cmake", "Qt6Multimedia"
                ),
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "QT_BUILD_TESTS": "ON",
                "QT_BUILD_TESTS_BY_DEFAULT": "OFF",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
                "QT_BUILD_BENCHMARKS": "OFF",
                "QT_BUILD_MANUAL_TESTS": "OFF",
                "FEATURE_speechd": "OFF",
                "FEATURE_flite": "OFF",
            }
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        for target in self._upstream_test_targets:
            cmake.build(target=target)
        if can_run(self):
            qtbase = self.dependencies["qtbase"].package_folder
            qtmultimedia = self.dependencies["qtmultimedia"].package_folder
            test_env = Environment()
            test_env.define("QT_QPA_PLATFORM", "offscreen")
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib"))
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase, "lib"))
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtmultimedia, "lib"))
            test_env.prepend_path("QT_PLUGIN_PATH", os.path.join(self.build_folder, "plugins"))
            test_env.prepend_path("QT_PLUGIN_PATH", os.path.join(qtbase, "plugins"))
            test_env.prepend_path("QT_PLUGIN_PATH", os.path.join(qtmultimedia, "plugins"))
            with test_env.vars(self).apply():
                self.run(
                    'ctest --test-dir "{}" --output-on-failure -j1 '
                    '-R "^(tst_qtexttospeech|tst_qvoice)$"'.format(
                        self.build_folder
                    )
                )

    def package(self):
        CMake(self).install()
        plugin_targets = os.path.join(
            self.package_folder,
            "lib",
            "cmake",
            "Qt6TextToSpeech",
            "Qt6QTextToSpeechMockPluginTargets-release.cmake",
        )
        replace_in_file(
            self,
            plugin_targets,
            'IMPORTED_NO_SONAME_RELEASE "TRUE"',
            'IMPORTED_SONAME_RELEASE "libqtexttospeech_mock.so"',
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if not os.path.islink(candidate) and self._elf_type(candidate) in (2, 3):
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool([objcopy, "--remove-section", ".codesign", unsigned])
                self._run_tool(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"]
                )
                if self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce an ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    @staticmethod
    def _run_tool(command):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to run {' '.join(command)}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Command {' '.join(command)} failed: {detail or result.returncode}"
            )
        return result.stdout

    @classmethod
    def _has_codesign_section(cls, objdump, path):
        return any(
            ".codesign" in line.split()
            for line in cls._run_tool([objdump, "-h", path]).splitlines()
        )

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(f"Unable to inspect {path}: {error}") from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(f"Unsupported ELF byte order in {path}")
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        candidate = os.environ.get(environment_variable) or executable
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            resolved = os.path.abspath(candidate)
        if not resolved:
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set {environment_variable}"
            )
        return os.path.abspath(resolved)

    def package_info(self):
        self.cpp_info.libs = ["Qt6TextToSpeech"]
        self.cpp_info.requires = ["qtbase::core", "qtmultimedia::qtmultimedia"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.set_property("cmake_target_name", "Qt6::TextToSpeech")
