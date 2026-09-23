import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibkdepimTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    def generate(self):
        CMakeDeps(self).generate()
        prefixes = []
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                prefixes.extend((
                    os.path.join(dependency.package_folder, "lib", "cmake"),
                    dependency.package_folder,
                ))
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as paths:
            paths.write(
                "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)\n"
                'list(PREPEND CMAKE_PREFIX_PATH "{}")\n'.format(";".join(prefixes))
            )
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = paths_file
        toolchain.generate()

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("kcompletion/6.18.0")
        self.requires("kcodecs/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(
            'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                self.build_folder
            ),
            env="conanrun",
        )
