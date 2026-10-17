#!/usr/bin/env python3
"""Conan recipe for the Qt 6.11.1 GUI foundation on HarmonyOS PC."""

import os
import shlex
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class QtbaseGuiConan(ConanFile):
    name = "qtbase-gui"
    version = "6.11.1"
    description = "Qt Core, Network, Gui and Widgets modules for HarmonyOS PC"
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtbase-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _has_pthread_cancel(self):
        """Detect whether pthread cancellation APIs can be compiled and linked."""
        # HarmonyOS may expose linkable compatibility stubs without providing
        # usable pthread cancellation semantics. Disable that Qt code path
        # explicitly instead of treating a successful stub link as support.
        if str(self.settings.os) == "OHOS":
            return False
        test_code = (
            "#include <pthread.h>\n"
            "int main(void) {\n"
            "    int old_state;\n"
            "    return pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, "
            "&old_state);\n"
            "}\n"
        )
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        # This probe controls a C++ compile definition, so test the same
        # compiler and flags that Qt will use for its C++ sources.
        configured_compiler = (
            compilers.get("cpp")
            or os.environ.get("CXX")
            or shutil.which("clang++")
            or shutil.which("c++")
        )
        if not configured_compiler:
            return False
        try:
            compiler_command = shlex.split(configured_compiler)
        except ValueError:
            return False
        if not compiler_command:
            return False
        compiler_flags = self.conf.get(
            "tools.build:cxxflags", default=[], check_type=list
        ) or []
        with tempfile.TemporaryDirectory(prefix="qt-pthread-check-") as temp_dir:
            source_path = os.path.join(temp_dir, "check.cpp")
            executable = os.path.join(temp_dir, "check")
            with open(source_path, "w", encoding="utf-8") as source_file:
                source_file.write(test_code)
            try:
                for link_flags in ([], ["-lpthread"]):
                    result = subprocess.run(
                        compiler_command
                        + compiler_flags
                        + [source_path]
                        + link_flags
                        + ["-o", executable],
                        capture_output=True,
                        timeout=30,
                    )
                    if result.returncode == 0:
                        return True
                return False
            except (OSError, subprocess.SubprocessError):
                return False

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables.update(
            {
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "QT_BUILD_TESTS": "ON",
                "QT_BUILD_TESTS_BY_DEFAULT": "OFF",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
                "FEATURE_gui": "ON",
                "FEATURE_network": "ON",
                "FEATURE_widgets": "ON",
                "FEATURE_graphicsview": "ON",
                "FEATURE_xml": "ON",
                "FEATURE_printsupport": "OFF",
                "FEATURE_sql": "OFF",
                "FEATURE_testlib": "ON",
                "FEATURE_dbus": "OFF",
                "FEATURE_openssl": "OFF",
                # Qt's public -no-opengl switch maps to INPUT_opengl=no.
                # FEATURE_opengl alone does not suppress the fatal OpenGL
                # functionality-test check in Qt 6.11's GUI configuration.
                "INPUT_opengl": "no",
                "FEATURE_opengl": "OFF",
                "FEATURE_opengles2": "OFF",
                "FEATURE_egl": "OFF",
                "FEATURE_eglfs": "OFF",
                "FEATURE_vulkan": "OFF",
                "FEATURE_xcb": "OFF",
                "FEATURE_xlib": "OFF",
                "FEATURE_linuxfb": "OFF",
                "FEATURE_vnc": "OFF",
                "FEATURE_evdev": "OFF",
                "FEATURE_libinput": "OFF",
                "FEATURE_mtdev": "OFF",
                "FEATURE_tslib": "OFF",
                "FEATURE_fontconfig": "OFF",
                "FEATURE_gtk3": "OFF",
                "FEATURE_accessibility_atspi_bridge": "OFF",
                "FEATURE_libudev": "OFF",
                "FEATURE_icu": "OFF",
                "FEATURE_pkg_config": "OFF",
                "FEATURE_system_zlib": "OFF",
                "FEATURE_system_pcre2": "OFF",
                "FEATURE_freetype": "ON",
                "FEATURE_system_freetype": "OFF",
                "FEATURE_harfbuzz": "ON",
                "FEATURE_system_harfbuzz": "OFF",
                "FEATURE_png": "ON",
                "FEATURE_system_png": "OFF",
                "FEATURE_jpeg": "ON",
                "FEATURE_system_jpeg": "OFF",
            }
        )

        # Append target-specific options instead of assigning
        # CMAKE_CXX_FLAGS, which would discard flags supplied by the
        # Conan profile, environment and compiler wrapper.
        if not self._has_pthread_cancel():
            tc.extra_cxxflags.append("-DQT_NO_PTHREAD_CANCEL")
            self.output.info(
                "pthread cancellation APIs unavailable; "
                "defining QT_NO_PTHREAD_CANCEL"
            )
        if str(self.settings.os) == "OHOS":
            # The OHOS Clang driver advertises the ARM crypto target feature,
            # but the platform arm_neon.h does not expose the AES intrinsics
            # used by Qt's optimized qHash implementation.
            tc.extra_cxxflags.append("-DQT_NO_ARM_AES_INTRINSICS")
            self.output.info(
                "ARM AES intrinsics unavailable; "
                "defining QT_NO_ARM_AES_INTRINSICS"
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_test_subset()

    def _run_upstream_test_subset(self):
        """Build and run the upstream test subset recorded in MANIFEST.yml.

        The full Qt test matrix is not built for the OHOS cross-compiled
        configuration; the representative suites listed in MANIFEST.yml are
        built explicitly and executed with the offscreen QPA backend.
        """
        build_folder = self.build_folder
        self.run(
            "cmake --build {} --target tst_qcolor tst_qhostaddress "
            "tst_qsizepolicy tst_qwidget tst_qimage tst_qpainter tst_qdom "
            "--parallel 1".format(shlex.quote(build_folder)),
            env="conanbuild",
        )
        qt_libs = self._locate_build_dir("lib")
        qt_plugins = self._locate_build_dir(os.path.join("plugins", "platforms"))
        self.run(
            "cmake -E env QT_QPA_PLATFORM=offscreen "
            "QT_QPA_PLATFORM_PLUGIN_PATH={} "
            "LD_LIBRARY_PATH={} "
            "ctest --test-dir {} --output-on-failure --parallel 1 "
            "-R '^(tst_qcolor|tst_qhostaddress|tst_qsizepolicy|tst_qwidget|tst_qimage|tst_qpainter|tst_qdom)$'".format(
                shlex.quote(qt_plugins),
                shlex.quote(qt_libs),
                shlex.quote(build_folder),
            ),
            env="conanbuild",
            ignore_errors=False,
        )

    def _locate_build_dir(self, rel_path):
        """Locate a directory inside the CMake build tree regardless of generator layout."""
        candidates = [
            os.path.join(self.build_folder, rel_path),
            os.path.join(self.build_folder, "Release", rel_path),
            os.path.join(self.build_folder, "Debug", rel_path),
        ]
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        return candidates[0]

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

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
        # Qt installs complete, relocatable Qt6Config.cmake files. Prevent
        # CMakeDeps from shadowing them with an incomplete generated config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        core = self.cpp_info.components["core"]
        core.libs = ["Qt6Core"]
        core.set_property("cmake_target_name", "Qt6::Core")

        network = self.cpp_info.components["network"]
        network.libs = ["Qt6Network"]
        network.requires = ["core"]
        network.set_property("cmake_target_name", "Qt6::Network")

        gui = self.cpp_info.components["gui"]
        gui.libs = ["Qt6Gui"]
        gui.requires = ["core"]
        gui.set_property("cmake_target_name", "Qt6::Gui")

        widgets = self.cpp_info.components["widgets"]
        widgets.libs = ["Qt6Widgets"]
        widgets.requires = ["core", "gui"]
        widgets.set_property("cmake_target_name", "Qt6::Widgets")

        xml = self.cpp_info.components["xml"]
        xml.libs = ["Qt6Xml"]
        xml.requires = ["core"]
        xml.set_property("cmake_target_name", "Qt6::Xml")
