import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class SombokTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not cross_building(self):
            # OHOS musl ignores DT_RUNPATH and conan injects no rpath
            # (§12.38③): aggregate the dependency libdirs by absolute path.
            libdirs = [
                os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
                for dep in self.dependencies.values()
                if dep.cpp_info.libdirs
            ]
            self.output.info(f"test libdirs={libdirs!r}")
            # self.run(env=[...]) takes env-script filenames, not KEY=VALUE —
            # pass the variable through the command line instead.
            self.run(
                f'LD_LIBRARY_PATH=":{":".join(libdirs)}" '
                f'"{os.path.join(self.cpp.build.bindir, "test_sombok")}"')
