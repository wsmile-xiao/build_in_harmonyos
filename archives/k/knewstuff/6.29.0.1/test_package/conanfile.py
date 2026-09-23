#!/usr/bin/env python3
"""Conan test_package for knewstuff 6.29.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KNewStuffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # KF6 packages are consumed with cmake_find_mode=none, so CMakeDeps
        # does not add their lib/cmake builddirs to CMAKE_PREFIX_PATH.  The
        # KF6NewStuffCore config calls find_dependency(KF6Attica) and needs
        # KF6AtticaConfig.cmake on the path, so add every dependency package
        # folder (including transitive KF6 deps such as attica/kpackage) here.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        # The installed KF6NewStuffCore target links its KF6 deps by bare -l
        # names (R05 relocatable DT_NEEDED), so this consumer must provide the
        # -L dirs to resolve libKF6Attica.so / libKF6CoreAddons.so etc. conf_info
        # feeds tools.build:*_linker_flags into the toolchain's CONAN_*_LINKER_FLAGS
        # (applied to CMAKE_*_LINKER_FLAGS_INIT), which tc.variables does not.
        lib_dirs = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
            and os.path.isdir(os.path.join(dep.package_folder, "lib"))
        ]
        if lib_dirs:
            ld_flags = ["-L{}".format(d) for d in lib_dirs]
            self.conf_info.append("tools.build:exe_linker_flags", ld_flags)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        tp_bin = os.path.join(self.build_folder, "..", "..", "bin")
        os.makedirs(tp_bin, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if libdir and os.path.isdir(libdir):
                for name in os.listdir(libdir):
                    if name.startswith("libKF6") and name.endswith(".so"):
                        link = os.path.join(tp_bin, name)
                        if not os.path.lexists(link):
                            os.symlink(os.path.join(libdir, name), link)

        env = Environment()
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        env.append(
            "QML2_IMPORT_PATH",
            [
                os.path.join(p.package_folder, "qml")
                for p in self.dependencies.values()
                if p.package_folder and os.path.isdir(os.path.join(p.package_folder, "qml"))
            ],
        )
        # QT_QPA_PLATFORM=offscreen: the knewstuff-dialog6 binary is a GUI tool;
        # offscreen lets the CLI path (--help/usage) run headless on the OH runtime.
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_knewstuff"),
                env="conanrun",
            )
            # OH-specific test: execute the packaged real platform binary
            # (knewstuff-dialog6). Loading and running it on the OHOS runtime
            # proves the relocatable linkage (R05), the platform binary and its
            # dynamic dependency chain resolve and execute on the target device.
            pkg = self.dependencies.get("knewstuff")
            dialog = (
                os.path.join(pkg.package_folder, "bin", "knewstuff-dialog6")
                if pkg and pkg.package_folder
                else None
            )
            if dialog and os.path.isfile(dialog):
                self.run('"{}" --help'.format(dialog), env="conanrun")
            else:
                raise ConanException(
                    "OH binary test: could not locate packaged knewstuff-dialog6"
                )
