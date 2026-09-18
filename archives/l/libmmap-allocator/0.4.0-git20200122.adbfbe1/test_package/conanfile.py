import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibmmapAllocatorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            target = "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            toolchain.variables["CMAKE_C_COMPILER_TARGET"] = f"{target}-linux-ohos"
            toolchain.variables["CMAKE_CXX_COMPILER_TARGET"] = f"{target}-linux-ohos"
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            cxx = compilers.get("cpp") or ""
            if cxx:
                sysroot = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(cxx))),
                    "sysroot",
                )
                if os.path.isdir(sysroot):
                    toolchain.variables["CMAKE_SYSROOT"] = sysroot.replace("\\", "/")
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_mmap_allocator"), env="conanrun")
        if str(self.settings.os) == "OHOS":
            self.run(
                os.path.join(bindir, "test_mmap_allocator_ohos"),
                env="conanrun",
            )
