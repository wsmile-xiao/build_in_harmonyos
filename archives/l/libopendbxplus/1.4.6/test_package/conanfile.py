from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LibopendbxplusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libopendbx provides libopendbx.so.1 (runtime dep of the C++ wrapper)
        # and the sqlite3 backend plugin used by the consumer test.
        self.requires("libopendbx/1.4.6")

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
        self.run("./opendbxplus_test '{backend}' .".format(backend=backend),
                 env="conanrun")
