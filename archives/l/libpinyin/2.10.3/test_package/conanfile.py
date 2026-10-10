"""Compile, link, and run a public-API consumer of libpinyin."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The consumer links the static Berkeley DB archive explicitly.
        # Make it a direct test requirement so Conan materializes its package.
        self.requires("berkeley-db/4.8.30")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        bdb_dep = self.dependencies["berkeley-db"]
        bdb = bdb_dep.cpp_info
        archive = os.path.join(
            bdb_dep.package_folder, bdb.libdirs[0],
            "lib" + (bdb.libs or ["db"])[0] + ".a",
        )
        path = os.path.join(self.generators_folder, "bdb_vars.cmake")
        with open(path, "w", encoding="utf-8") as stream:
            stream.write('set(BDB_STATIC_LIB "%s")\n' % archive.replace("\\", "/"))

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("cross build: consumer executable not run here")
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libpinyin")
        self.run(executable, env="conanrun")
