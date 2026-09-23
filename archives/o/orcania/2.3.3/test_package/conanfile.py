from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
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
        # The test_package binary is a tiny C consumer that links
        # Orcania::Orcania-static and exercises the public API. The
        # binary's return code is the canonical PASS/FAIL signal.
        import os
        bin_path = os.path.join(self.build_folder, "test_orcania")
        if not os.path.exists(bin_path):
            # CmakeLayout puts binaries under build/<config>/; fall back.
            bin_path = os.path.join(self.build_folder, "test_package")
        self.run(f'"{bin_path}"', cwd=self.build_folder)
