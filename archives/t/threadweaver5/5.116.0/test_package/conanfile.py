#!/usr/bin/env python3
"""Conan test_package for threadweaver5 5.116.0 (L1 official test).

Consumer-side verification (R34): the C++ test links KF5::ThreadWeaver and
drives the real public API — Queue, Job subclassing, JobPointer, Sequence,
Collection, stream()/enqueue() queueing helpers, make_job() lambdas,
QObjectDecorator signals and ResourceRestrictionPolicy — asserting observable
behaviour, not just that the library links.

HarmonyOS-specific assertions (R53): test.cpp additionally asserts that
  * the loaded libKF5ThreadWeaver.so carries the OHOS-required unversioned
    DT_SONAME and a DT_RUNPATH (E537: the installed ELF is linked with its
    final install RPATH and is never rewritten post-link, so OHOS keeps
    mmap'ing it PROT_EXEC);
  * the packaged ELF is re-signed with binary-sign-tool after install (the
    .codesign section is present on the packaged file).

test() really executes the built binary through self.run() (L0d / R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class ThreadWeaver5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        # Consume the native Qt5 configs shipped inside qt5-qtbase (the
        # CMakeDeps-generated ones would shadow them; the main-recipe
        # precedent).  The KF5ThreadWeaverConfig installed by the package is
        # found through its own lib/cmake prefix wired below.
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        # Same Linux platform force as the main recipe: the OHOS toolchain
        # maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS (no UNIX, flagged as a
        # cross build), which breaks the Qt5 config / AUTOMOC tool detection
        # for this consumer build.
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            if str(self.settings.arch) == "armv8":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            else:
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qt5 = self.dependencies.get("qt5-qtbase")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(pkg.package_folder)
            )
        if qt5:
            qt_pkg = qt5.package_folder
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(qt_pkg))
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(qt_pkg))
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(qt_pkg))
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(qt_pkg))
        # The generators folder holds the CMakeDeps-generated configs.
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        env = Environment()
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5 and qt5.package_folder:
            env.prepend_path("PATH", os.path.join(qt5.package_folder, "bin"))
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(qt5.package_folder, "lib"))
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        if pkg and pkg.package_folder:
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(pkg.package_folder, "lib"))
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5 and qt5.package_folder:
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(qt5.package_folder, "lib"))
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        if pkg and pkg.package_folder:
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(pkg.package_folder, "lib"))
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_threadweaver5"),
                env="conanrun",
            )
