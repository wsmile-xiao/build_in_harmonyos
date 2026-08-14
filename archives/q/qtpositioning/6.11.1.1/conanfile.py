#!/usr/bin/env python3
"""Conan recipe for Qt Positioning 6.11.1.1 on HarmonyOS PC (arm64)."""

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
    export_conandata_patches,
    get,
)


class QtpositioningConan(ConanFile):
    name = "qtpositioning"
    version = "6.11.1.1"
    description = "Qt Positioning module (positioning data sources and geo types) for HarmonyOS PC"
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtpositioning-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # PositioningQuick (the QtPositioning QML module) needs QtQuick, which
        # lives in qtdeclarative; without it qtlocation's assertTargets fails.
        self.requires("qtdeclarative/6.11.1")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtpositioning/6.11.1.1 in this recipe is a HarmonyOS PC adaptation"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # CMake has no Platform/HarmonyOS.cmake. On a HarmonyOS host it therefore
        # auto-detects CMAKE_SYSTEM_NAME=HarmonyOS and fails to set up the
        # shared-library SONAME/versioning rules. Presenting the platform as
        # Linux enables the standard platform rules; the OHOS clang driver
        # still targets aarch64-unknown-linux-ohos.
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

        # Let find_package(Qt6) locate qtbase's own Qt6Config.cmake package.
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        declarative_pkg = self.dependencies["qtdeclarative"].package_folder
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": qtbase_pkg,
                # PositioningQuick needs QtQuick (from qtdeclarative).
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH": declarative_pkg,
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "QT_BUILD_TESTS": "OFF",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
            }
        )
        tc.generate()

        # Build-time host tools (from qtdeclarative) need its lib dir on
        # LD_LIBRARY_PATH.
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(declarative_pkg, "lib"))
        env.vars(self).save_script("conanbuild_qt_libs")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._ensure_soname_symlinks()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _ensure_soname_symlinks(self):
        """Ensure libQt6Positioning.so and .so.6 links exist (E215: HMDFS breaks
        relative symlinks during install)."""
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, filenames in os.walk(libdir):
            for filename in filenames:
                if not filename.startswith("libQt6Positioning.so.6.11.1"):
                    continue
                real = os.path.join(root, filename)
                for link_name in ("libQt6Positioning.so.6", "libQt6Positioning.so"):
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
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
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
        return any(".codesign" in line.split() for line in section_table.splitlines())

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

    def package_info(self):
        # Qt installs complete, relocatable Qt6PositioningConfig.cmake files.
        # Prevent CMakeDeps from shadowing them with an incomplete generated config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        positioning = self.cpp_info.components["positioning"]
        positioning.libs = ["Qt6Positioning"]
        positioning.requires = ["qtbase::core"]
        positioning.set_property("cmake_target_name", "Qt6::Positioning")

        # PositioningQuick is the QtPositioning QML module (needs QtQuick).
        positioningquick = self.cpp_info.components["positioningquick"]
        positioningquick.libs = ["Qt6PositioningQuick"]
        positioningquick.requires = [
            "qtbase::core",
            "qtdeclarative::qml",
            "qtdeclarative::quick",
        ]
        positioningquick.set_property("cmake_target_name", "Qt6::PositioningQuick")
