from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import load


class LibopendbxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        odbx = self.dependencies["libopendbx"]
        backend = odbx.package_folder + "/lib/opendbx/libsqlite3backend.so"
        self.run("./opendbx_test '{backend}' .".format(backend=backend),
                 env="conanrun")
