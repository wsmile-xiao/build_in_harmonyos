#!/usr/bin/env python3
"""Conan recipe for adwaita-qt 1.4.2 on HarmonyOS PC."""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class AdwaitaQtConan(ConanFile):
    name = "adwaita-qt"
    version = "1.4.2"
    description = "Qt style library and plugin implementing the GNOME Adwaita look"
    license = "GPL-2.0-or-later AND LGPL-2.0-or-later"
    homepage = "https://github.com/FedoraQt/adwaita-qt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "adwaita-qt builds Qt style plugins and shared libraries"
            )
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("adwaita-qt supports Linux-compatible targets")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        qtbase = self.dependencies["qtbase"]
        qt_prefix = qtbase.package_folder.replace("\\", "/")

        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_EXAMPLE"] = "OFF"
        tc.cache_variables["USE_QT6"] = "ON"
        tc.cache_variables["QT_PLUGINS_DIR"] = "lib/qt6/plugins"
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["ADWAITAQT_VERSIONED_SHARED_LIBS"] = "OFF"
            for language in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"] = (
                    "-Wl,-soname,"
                )
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"] = (
                    "-Wl,-rpath,"
                )
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"] = ":"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"] = (
                    "-Wl,-rpath-link,"
                )
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()

        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as handle:
            handle.write(
                "\n".join(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{qt_prefix}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_prefix}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_prefix}/include")',
                        f'set(CONAN_RUNTIME_LIB_DIRS "{qt_prefix}/lib")',
                        "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
                    ]
                )
                + "\n"
            )

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE.GPL2", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE.LGPL2", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):
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
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["adwaitaqt6", "adwaitaqt6priv"]
        self.runenv_info.prepend_path(
            "QT_PLUGIN_PATH",
            os.path.join(self.package_folder, "lib", "qt6", "plugins"),
        )
