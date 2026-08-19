#!/usr/bin/env python3
"""Conan recipe for Qt Quick Timeline 6.11.1 on HarmonyOS PC."""

import os
import shlex
import shutil
import stat
import subprocess
import tempfile
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.env import Environment
from conan.tools.files import get


class QtquicktimelineConan(ConanFile):
    name = "qtquicktimeline"
    version = "6.11.1"
    description = "Qt Quick Timeline module for HarmonyOS PC"
    license = "GPL-3.0-only AND BSD-3-Clause"
    homepage = "https://doc.qt.io/qt-6/qtquicktimeline-index.html"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        # Qt Quick Timeline is a QML module: it requires Qt Quick (qtdeclarative)
        # on top of the qtbase Core/Gui stack.
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        class OhosLinuxPlatformBlock(Block):
            template = textwrap.dedent(
                """\
                # Treat the HarmonyOS host as Linux for CMake platform rules.
                # The OHOS clang driver already targets aarch64-unknown-linux-ohos.
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

        qtbase_pkg = self.dependencies["qtbase"].package_folder
        declarative_pkg = self.dependencies["qtdeclarative"].package_folder
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": qtbase_pkg,
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH": declarative_pkg,
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "QT_BUILD_TESTS": "ON",
                "QT_BUILD_TESTS_BY_DEFAULT": "OFF",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
                "QT_BUILD_BENCHMARKS": "OFF",
                "QT_BUILD_DOCS": "OFF",
            }
        )
        tc.generate()

        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(declarative_pkg, "lib"))
        env.vars(self).save_script("conanbuild_qt_libs")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_qml_tests()

    def _run_upstream_qml_tests(self):
        """Build and run the upstream QML auto tests with offscreen QPA."""
        cmake = CMake(self)
        test_targets = (
            "tst_qtquicktimeline",
            "tst_blendtrees",
        )
        for target in test_targets:
            cmake.build(target=target)
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        declarative_pkg = self.dependencies["qtdeclarative"].package_folder
        qt_libs = os.path.join(qtbase_pkg, "lib")
        declarative_libs = os.path.join(declarative_pkg, "lib")
        qt_plugins = os.path.join(qtbase_pkg, "plugins", "platforms")
        build_lib = os.path.join(self.build_folder, "lib")
        # The QML auto tests import QtQuick.Timeline / QtQuick.Timeline.BlendTrees.
        # Qt puts in-tree QML modules under the build dir (QT_BUILD_DIR + the
        # configured QML install dir), so expose the plausible module roots plus
        # the qtdeclarative/qtbase roots for the QtQuick dependency.
        qml_import_path = ":".join(
            [
                os.path.join(self.build_folder, "qml"),
                os.path.join(self.build_folder, "lib", "qml"),
                os.path.join(declarative_pkg, "qml"),
                os.path.join(declarative_pkg, "lib", "qml"),
                os.path.join(qtbase_pkg, "qml"),
                os.path.join(qtbase_pkg, "lib", "qml"),
            ]
        )
        pattern = "^({})$".format("|".join(test_targets))
        self.run(
            "cmake -E env QT_QPA_PLATFORM=offscreen "
            "QT_QPA_PLATFORM_PLUGIN_PATH={} "
            "QML2_IMPORT_PATH={} "
            "QML_IMPORT_PATH={} "
            "LD_LIBRARY_PATH={}:{}:{} "
            "ctest --test-dir {} --output-on-failure -R {} --parallel 1".format(
                shlex.quote(qt_plugins),
                shlex.quote(qml_import_path),
                shlex.quote(qml_import_path),
                shlex.quote(qt_libs),
                shlex.quote(declarative_libs),
                shlex.quote(build_lib),
                shlex.quote(self.build_folder),
                shlex.quote(pattern),
            ),
            env="conanbuild",
            ignore_errors=False,
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._ensure_soname_symlinks()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _ensure_soname_symlinks(self):
        """Ensure libQt6QuickTimeline.so / .so.6 links exist (E215: HMDFS
        breaks relative symlinks during install)."""
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, filenames in os.walk(libdir):
            for filename in filenames:
                if not filename.startswith("libQt6QuickTimeline.so.6.11.1"):
                    continue
                real = os.path.join(root, filename)
                for link_name in ("libQt6QuickTimeline.so.6", "libQt6QuickTimeline.so"):
                    link = os.path.join(root, link_name)
                    if not os.path.lexists(link):
                        os.symlink(filename, link)

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF executables and shared objects."""
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            has_codesign = self._has_codesign_section(objdump, binary)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if has_codesign:
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
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
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(
            ".codesign" in line.split()
            for line in section_table.splitlines()
        )

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if (
            not resolved
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            resolved = os.path.abspath(candidate)
        if (
            not resolved
            or not os.path.isfile(resolved)
            or not os.access(resolved, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    @staticmethod
    def _elf_type(path):
        """Return the ELF e_type value, or None for a non-ELF file."""
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    def package_info(self):
        self.cpp_info.libs = ["Qt6QuickTimeline"]
        # Qt installs a complete, relocatable Qt6QuickTimelineConfig.cmake.
        # Reuse it so consumers keep the upstream Qt6::QuickTimeline target
        # instead of a generated CMakeDeps config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.set_property("cmake_target_name", "Qt6::QuickTimeline")
