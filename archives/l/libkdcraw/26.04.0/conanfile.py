#!/usr/bin/env python3
"""Conan recipe for libkdcraw 26.04.0 on HarmonyOS PC (aarch64).

libkdcraw is the KDE RAW image decoding library wrapper around LibRaw
(thread-safe KDcrawIface::KDcraw class). Upstream 26.04.0 (KDE Gear 26.04)
is a Qt6 + ECM based CMake project; the library target is KDcraw with
OUTPUT_NAME KDcrawQt6 and the CMake package name is KDcrawQt6.

Upstream dependency closure (verified against the 26.04.0 CMakeLists.txt):
  - Qt6 Core + Gui (qtbase)
  - LibRaw >= 0.18 (libraw/0.22.1 from the ohpcd registry)
  - ECM (ecm/6.26.0, tool_requires) for KDEInstallDirs/KDECMakeSettings/
    KDECompilerSettings/ECMGenerateHeaders/ECMSetupVersion/
    ECMQtDeclareLoggingCategory/ECMGenerateExportHeader/
    ECMDeprecationSettings/FeatureSummary
No KF6 framework library is required at build or runtime.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass the KDE platform allowlist
    (OHOS is not in the upstream list)
  - CMAKE_POLICY_VERSION_MINIMUM=3.5 passed on the command line because
    the release tarball sets cmake_minimum_required(3.16) and the OHOS
    SDK's CMake 4.x deprecation policy refuses older compatibility
  - ECM_MODULE_PATH/ECM find-module paths are set explicitly because the
    CMakeDeps-generated ECMConfig does not propagate the variable the
    project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake is written manually because qtbase (and
    the other registry Qt/KF packages) use cmake_find_mode=none, which
    prevents CMakeDeps from adding their lib/cmake dirs to
    CMAKE_PREFIX_PATH
  - FindLibRaw (upstream cmake/modules/FindLibRaw.cmake) is a plain
    find_path/find_library module; LibRaw_INCLUDE_DIR/LIBRARIES resolve
    through CMAKE_PREFIX_PATH/CMAKE_LIBRARY_PATH/CMAKE_INCLUDE_PATH
    seeded with the libraw conan package folder
  - Upstream tests/ (raw2png, libinfo) are compiled with BUILD_TESTING=ON;
    upstream registers no add_test entry (manual tools), so ctest is 0
    upstream-side. Both tools are executed as smoke runs: libinfo prints
    the KDcraw/LibRaw version and capability strings; raw2png without
    arguments exits -1 with the usage banner (same behavior as upstream).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibkdcrawConan(ConanFile):
    name = "libkdcraw"
    version = "26.04.0"
    description = (
        "KDE RAW image decoding library wrapper around LibRaw "
        "(thread-safe KDcrawIface::KDcraw, DcrawInfoContainer, "
        "RawDecodingSettings)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/graphics/libkdcraw"
    url = "https://invent.kde.org/graphics/libkdcraw"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("libraw/0.22.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
            self._run_upstream_tools()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("lib",):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tools(self):
        # Upstream tests/ are manual tools registered without add_test:
        #   raw2png (RAW->PNG converter), libinfo (library capability dump).
        # Both are built with BUILD_TESTING=ON; execute them as smoke runs
        # on the build machine inside the build tree (OHOS binaries cannot
        # run on the build machine... they CAN here: same-arch host).
        # Their DT_NEEDED entries are build-tree-relative ("../bin/
        # libKDcrawQt6.so"), so the loader resolves them when cwd is the
        # tests/ CMake dir (build/Release/tests); run() with cwd set there.
        env = self._library_runtime_env()
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(test_tmp, exist_ok=True)
        env.define("HOME", test_home)
        env.define("TMPDIR", test_tmp)
        env.define("XDG_RUNTIME_DIR", os.path.join(self.build_folder, "xdg-runtime"))
        self._prepare_ctest_runtime_links()
        tools_dir = os.path.join(self.build_folder, "tests")
        with env.vars(self).apply():
            libinfo = os.path.join(self.build_folder, "bin", "libinfo")
            if os.path.isfile(libinfo):
                self.run(f'"{libinfo}"', cwd=tools_dir)
            raw2png = os.path.join(self.build_folder, "bin", "raw2png")
            if os.path.isfile(raw2png):
                # Usage banner run: exits -1 by design (upstream behavior)
                # when invoked without arguments.
                self.run(f'"{raw2png}"', cwd=tools_dir, ignore_errors=True)

    def _prepare_ctest_runtime_links(self):
        # Mirror libraw*/libQt6* next to the test tools so DT_NEEDED
        # entries resolve. Copies (not symlinks): HMDFS may deny symlink
        # creation in the CI sandbox.
        lib_mirrors = (
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "tests"),
        )
        lib_sources = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    self._glob_libraries(os.path.join(dep.package_folder, "lib"))
                )
        for mirror in lib_mirrors:
            os.makedirs(mirror, exist_ok=True)
            for src in lib_sources:
                dst = os.path.join(mirror, os.path.basename(src))
                if os.path.exists(dst):
                    continue
                try:
                    shutil.copy2(src, dst)
                except OSError as exc:
                    self.output.warning(f"copy2({src}, {dst}) failed: {exc}")

    @staticmethod
    def _glob_libraries(lib_dir):
        if not os.path.isdir(lib_dir):
            return []
        return [
            os.path.join(lib_dir, name)
            for name in os.listdir(lib_dir)
            if ".so" in name and os.path.isfile(os.path.join(lib_dir, name))
        ]

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()

    def package_info(self):
        # The project installs its own KDcrawQt6Config.cmake with proper
        # dependency tracking (find_dependency on Qt6Core/Qt6Gui). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it. The imported
        # target is KDcrawQt6 (EXPORT_NAME KDcrawQt6, empty namespace).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KDcrawQt6"]
        self.cpp_info.includedirs = ["include/KDcrawQt6"]
        self.cpp_info.set_property("cmake_file_name", "KDcrawQt6")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
