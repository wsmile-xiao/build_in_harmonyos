import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CbflibTestConan(ConanFile):
    """test_package for cbflib — builds a real C consumer that exercises the
    public libcbf API (write + read back a binary CBF) and runs it."""

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # cbf.h includes hdf5.h and static libcbf.a references pcreposix/H5*
        # symbols, so the consumer compiles/links against hdf5 and pcre
        # directly (their include dirs do not propagate through the tested
        # package's cpp_info.requires in this toolchain).
        self.requires("hdf5/1.14.6")
        self.requires("pcre/8.45")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the real consumer binary directly (L2 behavior evidence).
        consumer = os.path.join(self.cpp.build.bindirs[0], "consumer")
        self.run(consumer, env="conanrun")
