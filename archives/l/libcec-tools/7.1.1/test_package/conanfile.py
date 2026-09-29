import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibCecToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        os.umask(0o022)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libcec")
        cec_client = os.path.join(
            self.dependencies["libcec-tools"].package_folder,
            "bin", "cec-client")
        package_libdir = os.path.join(
            self.dependencies["libcec-tools"].package_folder, "lib")
        eudev_libdir = os.path.join(self.dependencies["eudev"].package_folder, "lib")
        runtime_libs = f"{package_libdir}:{eudev_libdir}:$LD_LIBRARY_PATH"
        self.run(f'LD_LIBRARY_PATH="{runtime_libs}" "{binary}" "{cec_client}"',
                 env="conanrun")

        for tool in ("cecc-client",):
            exe = os.path.join(self.dependencies["libcec-tools"].package_folder,
                               "bin", tool)
            if not os.path.isfile(exe):
                raise ConanException(f"installed tool not found: {exe}")
            self.run(f'LD_LIBRARY_PATH="{runtime_libs}" "{exe}" --help',
                     env="conanrun", quiet=False)
