from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Log4cplusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            sysroot = self.conf.get("tools.build:sysroot", default=None)
            if cross_building(self) and not sysroot:
                raise ConanInvalidConfiguration(
                    "OHOS cross-built consumers require tools.build:sysroot in the profile"
                )
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.variables["CMAKE_SYSTEM_VERSION"] = str(self.settings.os.version)
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.variables["CMAKE_C_COMPILER_TARGET"] = "aarch64-linux-ohos"
            tc.variables["CMAKE_CXX_COMPILER_TARGET"] = "aarch64-linux-ohos"
            tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-fuse-ld=lld"
            if sysroot:
                tc.variables["CMAKE_SYSROOT"] = str(sysroot).replace("\\", "/").rstrip("/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            return
        self.run("bin/log4cplus_consumer", env="conanrun")
