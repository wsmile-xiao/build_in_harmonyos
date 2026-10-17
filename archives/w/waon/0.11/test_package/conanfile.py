import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.errors import ConanException


class WaonTestConan(ConanFile):
    """Consumer test: drive the packaged waon binary over a synthesised WAV."""

    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _waon_path(self):
        dep = self.dependencies["waon"]
        bindir = dep.cpp_info.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder or "", bindir)
        return os.path.join(bindir, "waon")

    def build(self):
        waon = self._waon_path()
        if not os.path.exists(waon):
            raise ConanException("packaged waon not found: %s" % waon)
        tc = CMakeToolchain(self)
        tc.variables["WAON_BIN"] = waon.replace("\\", "/")
        tc.generate()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_waon")
        self.run(exe, env="conanrun")
