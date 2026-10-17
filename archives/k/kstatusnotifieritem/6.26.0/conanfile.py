#!/usr/bin/env python3
"""Conan recipe for kstatusnotifieritem 6.26.0 on HarmonyOS PC.

kstatusnotifieritem is a KDE Frameworks 6 library (libKF6StatusNotifierItem)
providing the freedesktop StatusNotifierItem system tray protocol.

OHOS-specific adaptations (following the kguiaddons/6.26.0 pattern):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection
  - WITHOUT_X11=ON: no X11 on OHOS, skip find_package(X11) entirely
  - USE_DBUS=OFF: headless OHOS baseline (ohpcd qtbase is built with
    FEATURE_dbus=OFF, so Qt6::DBus is unavailable); all DBus code paths are
    cleanly compiled out via upstream #if HAVE_DBUS guards
  - BUILD_PYTHON_BINDINGS=OFF: no Shiboken6/PySide6 on OHOS
  - 0001-disable-po-qm-processing.patch: ecm_install_po_files_as_qm and
    ecm_create_qm_loader require Qt6LinguistTools (not published to ohpcd)
  - Dependencies: qtbase/6.11.1, kwindowsystem/6.26.0; tool_requires ecm/6.26.0
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KstatusnotifieritemConan(ConanFile):
    name = "kstatusnotifieritem"
    version = "6.26.0"
    description = "KDE Frameworks 6 - StatusNotifierItem system tray protocol library"
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/frameworks/kstatusnotifieritem"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kwindowsystem/6.26.0")

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
        tc.variables["WITHOUT_X11"] = "ON"
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["BUILD_PYTHON_BINDINGS"] = "OFF"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        qtbase = self.dependencies.get("qtbase")
        kwindowsystem = self.dependencies.get("kwindowsystem")
        lines = []
        if kwindowsystem:
            # cmake_find_mode=none: its own KF6WindowSystemConfig.cmake is
            # the only provider; point CMake at its lib/cmake explicitly.
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{kwindowsystem.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines += [
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
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
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        from conan.tools.env import Environment

        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        for rel in ("bin", "lib", "tests"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        # Upstream ships a single test: tests/kstatusnotifieritemtest, an
        # interactive QApplication demo (main() ends in app.exec(), no
        # add_test() registration). We run it with QT_QPA_PLATFORM=offscreen
        # under a timeout: launching, constructing KStatusNotifierItem, and
        # surviving 8s in the event loop counts as a pass (rc=124 from
        # timeout); any earlier non-zero exit is a crash => fail.
        test_env = self._library_runtime_env()
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            matches = (glob.glob(os.path.join(self.build_folder, "bin", "kstatusnotifieritemtest"))
                       or glob.glob(os.path.join(self.build_folder, "tests", "kstatusnotifieritemtest")))
            if not matches:
                raise ConanException("upstream test binary not found after build")
            self.run(
                "timeout 8 {}; rc=$?; if [ $rc -ne 0 ] && [ $rc -ne 124 ]; then "
                "exit $rc; fi".format(matches[0])
            )

    def _prepare_ctest_runtime_links(self):
        # Materialize a compatibility bin/ dir one level above the build
        # folder so slash-containing DT_NEEDED entries resolve against CWD.
        import shutil

        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6StatusNotifierItemConfig.cmake with
        # proper dependency tracking. Use cmake_find_mode=none so CMakeDeps
        # doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6StatusNotifierItem"]
