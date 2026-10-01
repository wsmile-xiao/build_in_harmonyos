import os
import platform

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class OggfwdTestConan(ConanFile):
    """Consumer test: build a fake Icecast server and drive the packaged oggfwd against it."""

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        oggfwd = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "bin", "oggfwd")
        server = os.path.join(self.cpp.build.bindirs[0], "test_fake_icecast")
        if not os.path.isfile(oggfwd):
            raise ConanException(f"packaged oggfwd binary not found: {oggfwd}")
        if not os.path.isfile(server):
            raise ConanException(f"consumer test binary not built: {server}")
        # aarch64 ELF binaries only execute on an aarch64 host (an x86 runner
        # has no /lib/ld-musl-aarch64.so.1); otherwise only the build is checked.
        if cross_building(self) or platform.machine().lower() not in ("aarch64", "arm64"):
            self.output.warning("non-aarch64 host: consumer binary built and linked, runtime test skipped")
            return
        self.run(f'"{server}" "{oggfwd}"', env="conanrun")
