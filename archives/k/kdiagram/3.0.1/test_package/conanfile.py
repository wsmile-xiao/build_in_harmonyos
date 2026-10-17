#!/usr/bin/env python3
"""Conan test_package for kdiagram 3.0.1.

Consumer-side verification for the two-library chart payload:

* Part 1: find_package(KChart6) + find_package(KGantt6) through the
  installed KChart6Config.cmake / KGantt6Config.cmake — the exact
  mechanism eventviews (KDE PIM) uses to link KChart.
* Part 2: instantiate a KChart::Chart + a KChart::BarDiagram over a
  QStandardItemModel and a KGantt::View + ConstraintModel — exercising
  the exported KChart6::KChart6 / KGantt6::KGantt6 targets.
* Part 3: render the chart offscreen into a QImage and assert non-empty
  output; the KGantt side exercises the constrained model API.

The runtime environment mirrors the kinfocenter 6.7.2 / kfourinline
26.04.0 precedents: the OHOS loader gets /system/lib64 for
libc++_shared.so and the package lib dir resolves through
LD_LIBRARY_PATH plus build-tree compatibility symlinks.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KDiagramTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt6 Core/Gui/Widgets for the consumer + Qt6Svg (KChart6's
        # private dependency, needed at link time through the exported
        # target's INTERFACE closure on some linkers).
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2/kpeople5 precedent; required in
        # test_package too).
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        # Qt6 split-package component discovery: Qt6Svg lives in the
        # qtsvg package (kfourinline 26.04.0 verified pattern).
        qt_extra = []
        qtsvg = self.dependencies.get("qtsvg")
        if qtsvg and qtsvg.package_folder:
            qt_extra.append(qtsvg.package_folder)
        if qt_extra:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_extra
            )
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        # kdiagram (and the qtbase/qtsvg line) use cmake_find_mode=none,
        # so CMakeDeps doesn't put their lib/cmake dirs on
        # CMAKE_PREFIX_PATH — write the paths file manually (kfourinline
        # 26.04.0 precedent).
        prefixes = []
        libraries = []
        includes = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        self._prepare_runtime_links()
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        # L0 quality gate (stub_test_method) + main-branch precedent
        # (kfourinline 26.04.0 / kgoldrunner 26.04.0): execute the consumer
        # test binary explicitly through self.run() — cmake.test() alone is
        # flagged as a stub by the CI text scan. main.cpp carries the real
        # assertions (KChart::Chart + BarDiagram over QStandardItemModel,
        # KGantt::View + ConstraintModel, offscreen render non-empty check)
        # and exits non-zero on failure, so running it directly is the
        # actual test.
        # The OHOS-adapted conan 2.29.1 test_package has no
        # test_build_folder attribute — resolve through the layout's own
        # build folder (cmake_layout: same directory cmake.build() used).
        build_dir = getattr(self, "test_build_folder", None) or self.build_folder
        exe = None
        for cand in (
            os.path.join(build_dir, "kdiagram_consumer_test"),
            os.path.join(build_dir, "bin", "kdiagram_consumer_test"),
        ):
            if os.path.isfile(cand):
                exe = cand
                break
        if exe is None:
            hits = glob.glob(
                os.path.join(build_dir, "**", "kdiagram_consumer_test"),
                recursive=True,
            )
            if hits:
                exe = hits[0]
        if not exe:
            raise ConanException(
                "kdiagram_consumer_test binary not found in %s" % build_dir
            )
        env = self._runtime_env()
        with env.vars(self).apply():
            self.run('"%s"' % exe, cwd=build_dir)

    def _runtime_env(self):
        env = Environment()
        for dep in list(self.dependencies.values()):
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def _prepare_runtime_links(self):
        # The freshly built consumer test binary records a plain
        # libKChart6.so.3 DT_NEEDED; mirror the package libraries next to
        # the test binary so the loader resolves them from its CWD as
        # well (kinfocenter 6.7.2 precedent).
        package = None
        for dep in self.dependencies.values():
            if dep.ref.name == "kdiagram" and dep.package_folder:
                package = dep.package_folder
                break
        runtime_dirs = {
            os.path.join(self.build_folder, "bin"),
            self.build_folder,
        }
        lib_sources = []
        if package:
            lib_sources.extend(glob.glob(os.path.join(package, "lib", "lib*.so*")))
        for cdir in runtime_dirs:
            os.makedirs(cdir, exist_ok=True)
        for src in lib_sources:
            for cdir in runtime_dirs:
                dst = os.path.join(cdir, os.path.basename(src))
                if os.path.exists(src) and not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)
