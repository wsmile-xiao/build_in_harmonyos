"""Conan consumer: packaged unfoo extracts C input for an OHOS binary."""
import os
import platform
import shlex
import tarfile

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class UnfooTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "consumer.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-static"
        tc.generate()

    def build(self):
        archive = os.path.join(self.build_folder, "consumer.tar.gz")
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(os.path.join(self.source_folder, "consumer.c"), arcname="consumer.c")
        program = os.path.join(self.dependencies["unfoo"].package_folder, "bin", "unfoo")
        self.run("bash {} {}".format(shlex.quote(program), shlex.quote(archive)),
                 cwd=self.build_folder)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        consumer = os.path.join(self.cpp.build.bindirs[0], "unfoo_ohos_consumer")
        # Native OHOS aarch64 runners execute the binary directly; only an x86
        # build host needs qemu-aarch64 for the statically linked consumer.
        native = platform.machine().lower() in ("aarch64", "arm64")
        launcher = "" if native else "qemu-aarch64 "
        self.run("{}{}".format(launcher, shlex.quote(consumer)), cwd=self.build_folder)
