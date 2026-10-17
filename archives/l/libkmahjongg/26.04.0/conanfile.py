#!/usr/bin/env python3
"""Conan recipe for libkmahjongg 26.04.0 on HarmonyOS PC.

libkmahjongg is a KDE Gear library providing Mahjongg tileset/background
data and configuration widgets for KDE Mahjongg games.

OHOS-specific adaptations (pattern aligned with published kconfigwidgets
and ktextwidgets 6.x recipes):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: lconvert (qttools) fails to load libQt6Core
    at build time on this platform
  - BUILD_TESTING=OFF to skip upstream tests (no test suite present)
  - BUILD_SVG_CHECKS=OFF: optional SVG checks require ImageMagick (not needed)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project\'s CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake to CMAKE_PREFIX_PATH
  - Dependencies: qtbase/6.11.1, qtsvg/6.11.1, kconfig/6.14.0,
    kconfigwidgets/6.14.0, kcoreaddons/6.14.0, kwidgetsaddons/6.14.0,
    ki18n/6.14.0, ecm/6.20.0
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibkmahjonggConan(ConanFile):
    name = "libkmahjongg"
    version = "26.04.0"
    description = "KDE Gear - Mahjongg tileset and background library"
    license = "BSD-3-Clause"
    homepage = "https://invent.kde.org/graphics/libkmahjongg"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("kconfig/6.14.0")
        self.requires("kconfigwidgets/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("ki18n/6.14.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["BUILD_SVG_CHECKS"] = "OFF"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # qtbase's install carries Platform/HarmonyOS.cmake; without it
        # CMake treats HarmonyOS as an unknown platform.
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qtbase_platforms = os.path.join(
                qtbase.package_folder, "lib", "cmake", "Qt6", "platforms"
            )
            if os.path.isdir(qtbase_platforms):
                tc.variables["CMAKE_MODULE_PATH"] = qtbase_platforms

        CMakeDeps(self).generate()

        # Qt6Config.cmake (from qtbase) searches for components relative to
        # its own prefix.  qtsvg is a separate Conan package, so its
        # Qt6SvgConfig.cmake lives under qtsvg's prefix.  Point Qt6Svg_DIR
        # explicitly so find_package(Qt6 COMPONENTS Svg) succeeds.
        qtsvg = self.dependencies.get("qtsvg")
        if qtsvg:
            tc.variables["Qt6Svg_DIR"] = os.path.join(
                qtsvg.package_folder, "lib", "cmake", "Qt6Svg"
            )

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Sign installed OHOS ELF executables and shared objects."""
        import subprocess, tempfile
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
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            self._run_tool(
                [signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"],
                f"sign {binary}",
            )

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as f:
                header = f.read(18)
        except OSError:
            return None
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            return None
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(env_var, default):
        import shutil
        configured = os.environ.get(env_var)
        candidate = configured or default
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return os.path.abspath(candidate)
        raise FileNotFoundError(f"Tool {default} not found; set {env_var}")

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            raise FileNotFoundError(f"Unable to {action}: {e}") from e
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise FileNotFoundError(f"Unable to {action}: {detail}")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KMahjongg6"]
