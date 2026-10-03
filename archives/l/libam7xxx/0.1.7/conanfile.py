import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class Libam7xxxConan(ConanFile):
    name = "libam7xxx"
    version = "0.1.7"
    description = "Communication library for AM7XXX USB projectors and DPFs"
    license = "GPL-2.0-or-later"
    homepage = "https://git.ao2.it/libam7xxx.git/"
    url = "https://git.ao2.it/libam7xxx.git/"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        # Upstream's v0.1.7 tag retained the previous release's CMake version.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "set(PROJECT_VER_PATCH 5)", "set(PROJECT_VER_PATCH 7)")
        # OHOS provides the math functions in libc; its CMake platform module
        # is absent, so the generic find_library(m) returns MATH_LIB-NOTFOUND.
        replace_in_file(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"),
                        "  find_library(MATH_LIB m)",
                        '  if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")\n'
                        '    set(MATH_LIB "")\n'
                        '  else()\n'
                        '    find_library(MATH_LIB m)\n'
                        '  endif()')

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        dependency = self.dependencies["libusb"].cpp_info
        toolchain.cache_variables["LIBUSB_1_INCLUDE_DIRS"] = dependency.includedirs[0]
        toolchain.cache_variables["LIBUSB_1_LIBRARIES"] = os.path.join(
            dependency.libdirs[0], "libusb-1.0.so")
        toolchain.cache_variables["BUILD_PICOPROJ"] = False
        toolchain.cache_variables["BUILD_AM7XXX-PLAY"] = False
        toolchain.cache_variables["BUILD_am7xxx-modeswitch"] = False
        toolchain.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = True
        toolchain.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Asciidoc"] = True
        # CMake 4 rejects upstream's cmake_minimum_required(VERSION 2.6).
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"] if str(self.settings.os) == "OHOS" else None)

    def package(self):
        CMake(self).install()
        copy(self, "GPL-2", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            self._sign_shared_library()

    def _sign_shared_library(self):
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise RuntimeError("binary-sign-tool is required for OHOS shared libraries")
        libdir = os.path.join(self.package_folder, "lib")
        for filename in os.listdir(libdir):
            path = os.path.join(libdir, filename)
            if ".so" not in filename or os.path.islink(path):
                continue
            signed = path + ".signed"
            subprocess.run([signer, "sign", "-inFile", path,
                            "-outFile", signed, "-selfSign", "1"], check=True)
            os.replace(signed, path)
            os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["am7xxx"]
        self.cpp_info.set_property("cmake_file_name", "libam7xxx")
        self.cpp_info.set_property("cmake_target_name", "libam7xxx::libam7xxx")
        self.cpp_info.set_property("pkg_config_name", "libam7xxx")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
