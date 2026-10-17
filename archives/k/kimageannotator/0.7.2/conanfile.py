#!/usr/bin/env python3
"""Conan recipe -- kimageannotator 0.7.2 (ksnip kImageAnnotator, Qt image annotation).

kImageAnnotator provides the Qt Widgets image annotation surface used by
ksnip/flameshot. It is the direct downstream consumer of kcolorpicker/0.3.1
(the first-party Qt6 consumption precedent in this repo):
    find_package(kColorPicker-Qt6 0.3.1 REQUIRED)               # CMakeLists L47
    target_link_libraries(kImageAnnotator PUBLIC Qt6::Widgets Qt6::Svg
                                          PRIVATE kColorPicker::kColorPicker)  # L79
Build system: CMake >= 3.5, C++17, AUTOMOC/AUTORCC.
Artifact: libkImageAnnotator.so (VERSION 0.7.2 / SOVERSION 0).
Platform: OHOS aarch64, Qt6 route (BUILD_WITH_QT6=ON, consistent with the
KDE Frameworks 6 / qtsvg/6.11.1 stack already in this repo).
"""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KImageAnnotatorConan(ConanFile):
    name = "kimageannotator"
    version = "0.7.2"
    description = "kimageannotator -- ksnip Qt image annotation widget library (Qt6)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/ksnip/kImageAnnotator"
    url = "https://github.com/ksnip/kImageAnnotator"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_tests": [True, False],
    }
    default_options = {"shared": True, "fPIC": True, "build_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::Widgets (PUBLIC link) + Qt6::Test (upstream tests only)
        self.requires("qtbase/6.11.1")
        # Qt6::Svg (PUBLIC link): annotation tool icons are SVG resources
        self.requires("qtsvg/6.11.1")
        # PRIVATE link; ends up in the libkImageAnnotator.so DT_NEEDED closure
        self.requires("kcolorpicker/0.3.1")
        # Upstream: if (UNIX AND NOT APPLE) find_package(X11 REQUIRED).
        # CMake maps os=OHOS to a UNIX-like system and the OHOS clang driver
        # defines __linux__ (verified on device with -dM -E), so the X11 branch
        # is real: CapsLockStatusChecker.cpp calls XOpenDisplay/
        # XkbGetIndicatorState. Rely on the in-repo libx11/1.8.13 so the
        # built-in FindX11 module resolves through the conan package.
        self.requires("libx11/1.8.13", transitive_headers=True, transitive_libs=True)
        # X11/Xlib.h internally includes X11/X.h, X11/Xmd.h, X11/Xfuncproto.h
        # ... which are protocol headers shipped by xorgproto, NOT by libx11
        # (actiona/3.11.1 precedent). Pin the same version libx11/1.8.13
        # depends on so its headers join the include path transitively.
        self.requires("xorgproto/2025.1", transitive_headers=True, transitive_libs=True)
        if self.options.build_tests:
            # Upstream tests: find_package(GTest CONFIG REQUIRED) + GTest::gmock;
            # the googletest recipe exports GTestConfig.cmake (cmake_file_name=GTest)
            self.requires("googletest/1.17.0")

    def build_requirements(self):
        # translations/ calls find_package(Qt6LinguistTools) + qt_add_translation
        # (31 .qm files via lrelease). Qt6LinguistTools lives in qttools, not
        # qtbase; consumed as a host tool exactly like kdnssd/6.29.0 does.
        self.tool_requires("qt6linguisttools/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"]
        qtbase_cmake = os.path.join(qtbase.package_folder, "lib", "cmake")
        # qtbase ships cmake_find_mode=none (relocatable Qt6Config.cmake):
        # point Qt6 component DIRs at the packages directly (kcolorpicker/0.3.1
        # and karchive/6.19.0 consumption precedent).
        tc.cache_variables["Qt6_DIR"] = os.path.join(qtbase_cmake, "Qt6")
        tc.cache_variables["Qt6Widgets_DIR"] = os.path.join(qtbase_cmake, "Qt6Widgets")
        tc.cache_variables["Qt6Svg_DIR"] = os.path.join(
            self.dependencies["qtsvg"].package_folder, "lib", "cmake", "Qt6Svg")
        tc.cache_variables["Qt6Test_DIR"] = os.path.join(qtbase_cmake, "Qt6Test")
        # qtbase ships Platform/HarmonyOS.cmake (include Platform/Linux) under
        # lib/cmake/Qt6/platforms; expose it on CMAKE_MODULE_PATH so project()
        # loads a real platform module. Without it CMake treats HarmonyOS as
        # an unknown system: the UNIX variable stays undefined, so upstream's
        # "if (UNIX ...)" blocks (find_package(X11 REQUIRED), the translation
        # install dir, DesktopEnvironmentChecker) silently vanish and the
        # translations install() fails with "no DESTINATION" (qtsvg/6.11.1
        # same-device precedent for this exact mechanism).
        tc.cache_variables["CMAKE_MODULE_PATH"] = os.path.join(
            qtbase_cmake, "Qt6", "platforms")
        # Qt6Config.cmake consults QT_ADDITIONAL_PACKAGES_PREFIX_PATH for
        # component configs living outside qtbase (ksvg/6.26.0 and kirigami
        # 6.18.0 precedent) -- here: Qt6Svg in the qtsvg package.
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = \
            self.dependencies["qtsvg"].package_folder
        # translations/: Qt6LinguistTools is a tool_require (kdnssd/6.29.0
        # precedent); pin the config dir so find_package(Qt6LinguistTools)
        # resolves against the qt6linguisttools package.
        ltt = self.dependencies.build.get("qt6linguisttools")
        if ltt:
            tc.cache_variables["Qt6LinguistTools_DIR"] = os.path.join(
                ltt.package_folder, "lib", "cmake", "Qt6LinguistTools")
        # kColorPicker-Qt6 config exported by kcolorpicker/0.3.1
        tc.cache_variables["kColorPicker-Qt6_DIR"] = os.path.join(
            self.dependencies["kcolorpicker"].package_folder,
            "lib", "cmake", "kColorPicker-Qt6")
        # Upstream tests: find_package(GTest CONFIG REQUIRED); the googletest
        # package installs its own GTestConfig.cmake under lib/cmake/GTest.
        if self.options.build_tests:
            tc.cache_variables["GTest_DIR"] = os.path.join(
                self.dependencies["googletest"].package_folder,
                "lib", "cmake", "GTest")
        # X11: the built-in FindX11 module does plain find_path/find_library;
        # add the libx11 package to CMAKE_PREFIX_PATH (actiona/3.11.1
        # precedent) and pin the exact cache variables so the search succeeds
        # regardless of the SDK toolchain find-root modes (flameshot/14.0.0
        # precedent for CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY interference).
        x11_pkg = self.dependencies["libx11"].package_folder
        xproto_pkg = self.dependencies["xorgproto"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = x11_pkg
        # FindX11's X11::X11 imported target carries X11_X11_INCLUDE_PATH as
        # INTERFACE_INCLUDE_DIRECTORIES: it must cover BOTH the libx11 headers
        # (Xlib.h/XKBlib.h) and the xorgproto protocol headers (X.h/Xmd.h/...)
        # included by Xlib.h internally.
        tc.cache_variables["X11_X11_INCLUDE_PATH"] = os.path.join(
            x11_pkg, "include") + ";" + os.path.join(xproto_pkg, "include")
        tc.cache_variables["X11_X11_LIB"] = os.path.join(x11_pkg, "lib", "libX11.so")

        # SONAME fix (knowledge draft DRAFT-cmake-harmonyos-system-name-soname,
        # second independent hit after kcolorpicker/0.3.1): CMake ships no
        # Platform/HarmonyOS module for CMAKE_SYSTEM_NAME=HarmonyOS, so the
        # platform SONAME flag variables stay undefined and artifacts get no
        # DT_SONAME (downstream DT_NEEDED would then embed package-cache
        # absolute paths, which are not relocatable). Restore the flags
        # explicitly; CMAKE_PLATFORM_NO_VERSIONED_SONAME skips versioned
        # symlink creation, which HMDFS paths do not support.
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        # Explicit link closure (implement-policy item 5 / build-chain-pitfalls
        # "lld implicit resolution" entry): the OHOS toolchain emits no
        # -rpath-link (no HarmonyOS platform module), and libkImageAnnotator.so
        # carries PUBLIC Qt6 + PRIVATE kColorPicker + PRIVATE X11 in its
        # DT_NEEDED closure, with libX11 pulling libxcb/libXau transitively.
        # Declare every dependency libdir explicitly instead of relying on
        # lld's silent skip-on-miss behaviour (--no-allow-shlib-undefined only
        # checks DSOs resolvable via the DEFAULT search path).
        link_dirs = [os.path.join(self.build_folder, "lib")]
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                path = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(path) and path not in link_dirs:
                    link_dirs.append(path)
        rpath_link = " ".join("-Wl,-rpath-link," + d for d in link_dirs)
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = rpath_link
        tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = rpath_link

        tc.variables["BUILD_WITH_QT6"] = "ON"
        # Upstream default ON; no example executable on the device
        tc.variables["BUILD_EXAMPLE"] = "OFF"
        tc.variables["BUILD_TESTS"] = "ON" if self.options.build_tests else "OFF"
        # Real compile/link lines into the CI log as explicit-closure evidence
        tc.variables["CMAKE_VERBOSE_MAKEFILE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream tests: 49 CTest executables (tests/CMakeLists.txt
        # UNITTEST_SRC), GTest CONFIG + Qt6::Test, each linking a rebuilt
        # static copy of the sources (KIMAGEANNOTATOR_STATIC) plus the shared
        # libkImageAnnotator.so. No display server on the device -> offscreen
        # QPA (qtbase/6.11.1, kcolorpicker/0.3.1, qtsvg/6.11.1 same-device
        # precedent; upstream CHANGELOG 0.7.2 explicitly fixed
        # KeyInputHelperTest for QT_QPA_PLATFORM=offscreen).
        # Runtime closure: no HarmonyOS platform module -> no build-tree
        # RPATH, and the loader default path has no Qt/conan libraries, so
        # every runtime libdir must be injected explicitly (E135/E285/E312).
        if self.options.build_tests and can_run(self):
            test_env = Environment()
            test_env.define("QT_QPA_PLATFORM", "offscreen")
            test_env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
            # qtbase ships no fonts and fontconfig is absent; the offscreen
            # QPA font database would end up empty and text rendering inside
            # the annotation widgets crashes. Point the offscreen platform at
            # the standard OHOS system font directory.
            if os.path.isdir("/system/fonts"):
                test_env.define("QT_QPA_FONTDIR", "/system/fonts")
            test_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib"))
            for dep in self.dependencies.host.values():
                if not dep.package_folder:
                    continue
                for libdir in dep.cpp_info.libdirs:
                    path = os.path.join(dep.package_folder, libdir)
                    if os.path.isdir(path):
                        test_env.append_path("LD_LIBRARY_PATH", path)
            with test_env.vars(self).apply():
                # enable_testing() lives in the tests/ SUBDIRECTORY, so the
                # CTestTestfile is generated there, not at the build root.
                self.run(
                    "ctest --output-on-failure -j1",
                    cwd=os.path.join(self.build_folder, "tests"))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF files (E077 four-step flow).

        CMake install strips the build-tree RPATH, which rewrites the ELF and
        invalidates the link-time .codesign section; altered/unsigned ELF
        files fail to load with "operation not permitted" (E077/E135). Flow:
        remove old signature -> (re)sign -> restore permissions.
        """
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
                    prefix=".conan-sign-", dir=os.path.dirname(binary)) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}")
                self._run_tool(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
                    f"sign {binary}")
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}")
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}")
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}")
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
        # Public headers install to include/kImageAnnotator-Qt6/kImageAnnotator
        # (upstream INSTALL_INTERFACE layout); the public headers include
        # "kImageAnnotator/..." so the include root is kImageAnnotator-Qt6.
        self.cpp_info.includedirs = [os.path.join("include", "kImageAnnotator-Qt6")]
        self.cpp_info.libs = ["kImageAnnotator"]
        # Downstream contract (upstream CMakeLists L113/L115/L134/L140):
        #   find_package(kImageAnnotator-Qt6 0.7.2 REQUIRED)
        #   target_link_libraries(... kImageAnnotator::kImageAnnotator)
        self.cpp_info.set_property("cmake_file_name", "kImageAnnotator-Qt6")
        self.cpp_info.set_property("cmake_target_name", "kImageAnnotator::kImageAnnotator")
        # The package ships its own relocatable kImageAnnotator-Qt6Config.cmake;
        # keep CMakeDeps from shadowing it with a generated config (qtsvg
        # precedent).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
