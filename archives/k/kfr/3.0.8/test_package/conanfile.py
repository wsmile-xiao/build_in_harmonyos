from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The CI L0d quality gate statically requires a self.run() call inside
        # test(); a bare cmake.test() is rejected as a stub:
        #     [fail] L0d: test() method has no self.run() call
        # Running the consumer binary directly is also stronger evidence: its
        # assertion lines appear verbatim in the CI log.
        import os
        candidates = [
            os.path.join(self.build_folder, "test_kfr"),
            os.path.join(self.build_folder, "test_package"),
        ]
        bin_path = next((c for c in candidates if os.path.exists(c)), None)
        if bin_path is None:
            raise ConanException(
                "test_kfr binary not found; looked in: {}".format(candidates))
        self.run('"{}"'.format(bin_path), cwd=self.build_folder)
