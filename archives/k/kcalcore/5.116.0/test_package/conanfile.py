#!/usr/bin/env python3
"""Conan test_package for kcalcore 5.116.0 (L1 official test).

Consumer-side verification (R34): the C++ test links KF5::CalendarCore and
drives the real public API the way the downstream KDE PIM consumers
(eventviews et al.) use it — MemoryCalendar + Event/Todo management, the
ICalFormat toString/fromRawString round-trip through the libical-backed
parser inside the packaged libKF5CalendarCore.so, the VCalFormat vCalendar
export — plus HarmonyOS-specific checks (R53): the packaged library
carries the OHOS-required unversioned DT_SONAME and a DT_RUNPATH (E537
install-RPATH adaptation), parsed straight from the ELF dynamic section of
the consumer-visible package path.

test() really executes the built binary through self.run() (L0d / R34).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KCalCoreTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("libical3/3.0.20")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Same Linux-like platform force as the library build (chain-
            # wide convention, kpeople5 precedent): the native Qt5 configs
            # apply their POSIX settings and the consumer build behaves
            # exactly like the library build it verifies.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            if str(self.settings.arch) == "armv8":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            elif str(self.settings.arch) == "x86_64":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "x86_64"
        tc.generate()

        pkg = self.dependencies.get("kcalcore")
        qtbase = self.dependencies.get("qt5-qtbase")
        libical = self.dependencies.get("libical3")
        # Same native-config wiring as the library build: the recipe's
        # package_info exposes the project-installed KF5CalendarCoreConfig.
        # cmake (cmake_find_mode=none) and qt5-qtbase ships its native Qt5
        # configs, so both package roots are wired onto the CMake search
        # paths through conan_cmakedeps_paths.cmake (kcoreaddons5 /
        # kpeople5 test_package precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg and pkg.package_folder:
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                % pkg.package_folder
            )
        if qtbase and qtbase.package_folder:
            qt_pkg = qtbase.package_folder
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % qt_pkg)
        if libical and libical.package_folder:
            # KF5CalendarCoreConfig.cmake only find_dependency's LibIcal
            # for static builds, but keep the package root reachable for
            # completeness.
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % libical.package_folder)
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _build_env(self):
        # The Qt host tools executed during configure (if any) need the
        # compatible libc++ loaded first (kpeople5 test_package precedent).
        env = Environment()
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def _stage_libical_runtime(self):
        # libical3/3.0.20 ships OHOS relative sonames ("./libical.so"): the
        # musl loader resolves DT_NEEDED entries containing a slash from
        # the process CWD, not from LD_LIBRARY_PATH.  The packaged
        # libKF5CalendarCore.so NEEDs ./libical.so, so the libical
        # libraries are staged next to the execution CWD and next to the
        # test binaries (kcalendarcore 6.26.0 test_package precedent).
        libical = self.dependencies.get("libical3")
        if not (libical and libical.package_folder):
            return
        targets = [self.build_folder]
        for bindir in self.cpp.build.bindirs:
            if bindir and os.path.abspath(bindir) != os.path.abspath(self.build_folder):
                targets.append(bindir)
        for target_dir in targets:
            os.makedirs(target_dir, exist_ok=True)
            for lib_src in sorted(
                glob.glob(
                    os.path.join(libical.package_folder, "lib", "libical*.so")
                )
            ):
                lib_dst = os.path.join(target_dir, os.path.basename(lib_src))
                if not os.path.exists(lib_dst):
                    shutil.copy2(lib_src, lib_dst)

    def test(self):
        if not can_run(self):
            return
        self._stage_libical_runtime()
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("TZ", "UTC")
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kcalcore"),
                env="conanrun",
            )
