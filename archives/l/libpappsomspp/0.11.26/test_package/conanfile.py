#!/usr/bin/env python3
"""Consumer test for libpappsomspp 0.11.26.

Upstream ships a Catch2 suite (41 test source files, 60 TEST_CASEs, 1484
assertions) that is built and executed by the recipe itself when
with_tests=True (the default in this port). This consumer test backs the
packaging with real API usage of the delivered core library:
AaStringCodec decode, FilterGreatestY on an inline mass spectrum, and
mass-to-code matching — the same core APIs the upstream suite exercises,
through the packaged headers and libs.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, cmake_layout


class LibpappsomsppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("liblzf/3.6")
        self.requires("libodsstream/0.9.18")
        self.requires("libpwizlite/3.0.14")
        self.requires("boost/1.84.0")
        self.requires("zlib/1.3.1")
        self.requires("zstd/1.5.7")
        self.requires("sqlite3/3.53.4")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # PappsoMSppConfig.cmake (installed with the package) declares
        # find_dependency names for the Qt components and the chain
        # packages. qtbase & friends use cmake_find_mode=none (their own
        # upstream configs under lib/cmake), so wire their package dirs
        # into CMAKE_PREFIX_PATH through conan_cmakedeps_paths.cmake
        # (libodsstream precedent).
        deps = CMakeDeps(self)
        # libpappsomspp ships its own PappsoMSppConfig.cmake (upstream
        # install(EXPORT)) — use it, not a CMakeDeps-generated one.
        deps.set_property("libpappsomspp", "cmake_find_mode", "none")
        # OdsStream ships a usable upstream install(EXPORT) config under
        # its package lib/cmake — use it (the CMakeDeps-generated one pulls
        # find_dependency(qtbase) which has no config). PwizLite's upstream
        # config hardcodes /usr paths — use the CMakeDeps-generated one.
        deps.set_property("libodsstream", "cmake_find_mode", "none")

        deps.generate()
        lines = []
        tested = self.dependencies.get("libpappsomspp")
        if tested:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "'
                f'{tested.package_folder}/lib/cmake")'
            )
        for name in ("qtbase", "qt5compat", "qtbase-sql-dbus",
                     "qtdeclarative", "qtsvg", "libodsstream",
                     "libpwizlite"):
            dep = self.dependencies.get(name)
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "'
                    f'{os.path.join(dep.package_folder, "lib", "cmake")}")'
                )
        paths_file = os.path.join(self.generators_folder,
                                  "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        # The presets-based configure does not read our custom file
        # directly; export the plain path list for the CMakeLists ENV hook.
        # qtbase first: only its Qt6/Qt6Sql/Qt6Svg configs are complete
        # (the qtbase-sql-dbus package dir has an empty-shelled Qt6 tree).
        # Resolve the qtbase package folder through the dependency graph,
        # not through directory-name heuristics.
        qtbase = self.dependencies.get("qtbase")
        qtbase_cm = (os.path.join(qtbase.package_folder, "lib", "cmake")
                     if qtbase and qtbase.package_folder else None)
        ordered = [seg.split('"')[1]
                   for seg in lines if seg.startswith("list(")]
        if qtbase_cm and qtbase_cm in ordered:
            ordered.remove(qtbase_cm)
            ordered.append(qtbase_cm)  # last PREPEND entry = first in path
        # The generators folder hosts the CMakeDeps configs for the chain
        # packages (liblzf-*.cmake, OdsStreamConfig.cmake, ...) — it must be
        # on the prefix path too.
        ordered.insert(0, self.generators_folder)
        self._prefix_paths = ";".join(ordered)

    def build(self):
        cmake = CMake(self)
        from conan.tools.env import Environment
        env = Environment()
        env.define("PAPPSOMSPP_PREFIX_PATHS", self._prefix_paths)
        # Qt module packages other than qtbase (qtsvg/qtdeclarative/
        # qt5compat/qtbase-sql-dbus) — for the qtbase Qt6Config to resolve
        # Svg/Qml/Core5Compat components living outside qtbase.
        qt_extra = ";".join(
            p for p in self._prefix_paths.split(";")
            if p and not p.startswith(
                os.path.dirname(self.dependencies["qtbase"].package_folder))
        )
        env.define("PAPPSOMSPP_QT_EXTRA_PREFIX", qt_extra)
        tested = self.dependencies.get("libpappsomspp")
        if tested and tested.package_folder:
            env.define("PAPPSOMSPP_TARGETS_DIR",
                       os.path.join(tested.package_folder,
                                    "lib", "cmake", "pappsomspp"))
        with env.vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        # cmake_layout puts the binary in the build folder root.
        cmd = os.path.join(self.build_folder, "test_pappsomspp")
        from conan.tools.env import Environment
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(dep.package_folder, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run(f'"{cmd}"', env="conanrun")
