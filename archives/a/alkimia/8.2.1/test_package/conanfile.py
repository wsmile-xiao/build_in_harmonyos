#!/usr/bin/env python3
"""Conan test_package for alkimia 8.2.1.

Verifies that the Alkimia::alkimia library can be found via the installed
LibAlkimia6Config.cmake and that the AlkValue (GMP-backed arbitrary
precision monetary value) API is callable (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class AlkimiaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("gmp/6.3.0.1")
        self.requires("knewstuff/6.29.0.1")
        self.requires("kcompletion/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kitemviews/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kcodecs/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")

    def build_requirements(self):
        # LibAlkimia6Config.cmake find_dependency(KF6) needs ECM's FindKF6
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # alkimia (and its KF6 deps) are consumed with cmake_find_mode=none,
        # so CMakeDeps does not add their lib/cmake builddirs to
        # CMAKE_PREFIX_PATH (knewstuff test_package precedent). The
        # LibAlkimia6Config.cmake find_dependency()s GMP/Qt6/KF6 configs, so
        # every dependency package folder must be on the search path.
        lines = []
        dep_order = (
            "alkimia",
            "qtbase-sql-dbus",
            "qtdeclarative",
            "gmp",
            "knewstuff",
            "kcompletion",
            "kiconthemes",
            "kxmlgui",
            "kconfigwidgets",
            "kguiaddons",
            "kcolorscheme",
            "kitemviews",
            "kconfig",
            "kcoreaddons",
            "ki18n",
            "kcodecs",
            "kwidgetsaddons",
            "karchive",
            "kpackage",
            "attica",
            "zlib",
            "openssl",
            "zstd",
            "dbus",
        )
        for dep_name in dep_order:
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                pkg = dep.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
                kf6_inc = os.path.join(pkg, "include", "KF6")
                if os.path.isdir(kf6_inc):
                    for module in sorted(os.listdir(kf6_inc)):
                        mod_dir = os.path.join(kf6_inc, module)
                        if os.path.isdir(mod_dir):
                            lines.append(
                                f'list(PREPEND CMAKE_INCLUDE_PATH "{mod_dir}")'
                            )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        # ECM's FindKF6.cmake is needed by LibAlkimia6Config.cmake's
        # find_dependency(KF6 COMPONENTS Config)
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            ecm_find = os.path.join(ecm.package_folder, "share", "ECM", "find-modules")
            ecm_modules = os.path.join(ecm.package_folder, "share", "ECM", "modules")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_find}")')
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_modules}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        with self._test_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _test_env(self):
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("TZ", "UTC")
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def test(self):
        # conan's test() runs "./test_package" through a plain shell; inject
        # the runtime library path through os.environ directly so the OHOS
        # musl loader finds the conan-cached shared objects.
        lib_dirs = [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ]
        if self.settings.os == "OHOS":
            # libc++_shared.so compatible with the sandbox runner
            lib_dirs.append("/system/lib64")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["TZ"] = "UTC"
        # The published kconfig package carries a relative DT_NEEDED entry
        # `../../bin/libKF6ConfigCore.so` (from its own build tree layout).
        # The OHOS musl loader resolves path-style NEEDED entries relative to
        # the process cwd; with cwd=<test_package build folder> the entry
        # points two levels up, so materialize a symlink shim there
        # (knewstuff test_package precedent).
        shim_dir = os.path.abspath(
            os.path.join(self.build_folder, "..", "..", "bin")
        )
        os.makedirs(shim_dir, exist_ok=True)
        for dep_name, lib in (
            ("kconfig", "libKF6ConfigCore.so"),
            ("knewstuff", "libKF6NewStuffCore.so"),
        ):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                src = os.path.join(dep.package_folder, "lib", lib)
                dst = os.path.join(shim_dir, lib)
                if os.path.exists(src) and not os.path.exists(dst):
                    os.symlink(src, dst)
        cmd = os.path.join(self.cpp.build.bindir, "test_package")
        self.run(f'"{cmd}"')
