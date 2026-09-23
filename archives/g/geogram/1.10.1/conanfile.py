#!/usr/bin/env python3
"""Conan recipe for Geogram 1.10.1."""

import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, get


class GeogramConan(ConanFile):
    name = "geogram"
    version = "1.10.1"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch not in ("armv8", "arm64-v8a"):
            raise ConanInvalidConfiguration("Geogram OHOS package requires armv8/arm64-v8a")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # The complete release asset vendors Geogram's third-party sources.
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def _platform(self):
        if self.settings.os == "OHOS":
            return "OHOS-clang"
        if self.settings.os == "Windows":
            if str(self.settings.compiler) in ("msvc", "Visual Studio"):
                return "Win-vs-dynamic-generic" if self.options.shared else "Win-vs-generic"
            return "Win64-gcc"
        if str(self.settings.compiler) == "clang":
            return "Linux64-clang-dynamic" if self.options.shared else "Linux64-clang"
        return "Linux64-gcc-dynamic" if self.options.shared else "Linux64-gcc"

    def _ohos_toolchain(self):
        candidates = []
        user_toolchain = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list
        )
        candidates.extend(user_toolchain)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake"))
        candidates.extend(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"
            )
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        # The bare OHOS worker ships a target clang/sysroot but no CMake file.
        # Generate a task-local toolchain so Conan never writes the shared SDK.
        sdk = os.environ.get("OHOS_SDK_ROOT", "/storage/Users/currentUser/usr/local")
        compiler = os.path.join(sdk, "bin", "clang")
        compiler_cxx = os.path.join(sdk, "bin", "clang++")
        sysroot = os.path.join(sdk, "sysroot")
        if not (os.path.isfile(compiler) and os.path.isfile(compiler_cxx)):
            raise ConanInvalidConfiguration(
                "找不到 OHOS clang：请配置 OHOS_SDK_ROOT 或 user_toolchain"
            )
        path = os.path.join(self.build_folder, "geogram-ohos-toolchain.cmake")
        os.makedirs(self.build_folder, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as toolchain:
            toolchain.write("set(CMAKE_SYSTEM_NAME OHOS)\n")
            toolchain.write("set(CMAKE_SYSTEM_PROCESSOR aarch64)\n")
            toolchain.write("set(CMAKE_C_COMPILER \"{}\")\n".format(compiler.replace("\\", "/")))
            toolchain.write("set(CMAKE_CXX_COMPILER \"{}\")\n".format(compiler_cxx.replace("\\", "/")))
            toolchain.write("set(CMAKE_SYSROOT \"{}\")\n".format(sysroot.replace("\\", "/")))
            toolchain.write("set(CMAKE_C_COMPILER_TARGET aarch64-unknown-linux-ohos)\n")
            toolchain.write("set(CMAKE_CXX_COMPILER_TARGET aarch64-unknown-linux-ohos)\n")
            toolchain.write("set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)\n")
            toolchain.write("set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)\n")
            toolchain.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)\n")
            toolchain.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)\n")
        return path

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["VORPALINE_PLATFORM"] = self._platform()
        tc.variables["VORPALINE_BUILD_DYNAMIC"] = bool(self.options.shared)
        tc.variables["GEOGRAM_WITH_GRAPHICS"] = False
        tc.variables["GEOGRAM_WITH_TBB"] = False
        tc.variables["GEOGRAM_WITH_LEGACY_NUMERICS"] = False
        tc.variables["GEOGRAM_WITH_EXPLORAGRAM"] = False
        tc.variables["GEOGRAM_LIB_ONLY"] = True
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()
        CMakeDeps(self).generate()

    def _cmake_variables(self):
        variables = {
            "VORPALINE_PLATFORM": self._platform(),
            "VORPALINE_BUILD_DYNAMIC": bool(self.options.shared),
            "GEOGRAM_WITH_GRAPHICS": False,
            "GEOGRAM_WITH_TBB": False,
            "GEOGRAM_WITH_LEGACY_NUMERICS": False,
            "GEOGRAM_WITH_EXPLORAGRAM": False,
            "GEOGRAM_LIB_ONLY": True,
            "CMAKE_INSTALL_LIBDIR": "lib",
        }
        if self.settings.os == "OHOS":
            variables["CMAKE_TOOLCHAIN_FILE"] = self._ohos_toolchain()
            variables["OHOS_ARCH"] = "arm64-v8a"
            variables["CMAKE_SHARED_LINKER_FLAGS"] = "-pthread -ldl -lm"
        return variables

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        old_umask = os.umask(0) if self.settings.os == "OHOS" else None
        try:
            cmake.configure(variables=self._cmake_variables())
            cmake.build()
        finally:
            if old_umask is not None:
                os.umask(old_umask)

    def package(self):
        old_umask = os.umask(0) if self.settings.os == "OHOS" else None
        try:
            CMake(self).install()
            if self.settings.os == "OHOS":
                self._sign_shared_libraries()
        finally:
            if old_umask is not None:
                os.umask(old_umask)

    def _sign_shared_libraries(self):
        sdk = os.environ.get("OHOS_SDK_ROOT", "/storage/Users/currentUser/usr/local")
        signer = shutil.which("binary-sign-tool") or os.path.join(sdk, "bin", "binary-sign-tool")
        objcopy = shutil.which("llvm-objcopy") or os.path.join(sdk, "bin", "llvm-objcopy")
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("OHOS native binary-sign-tool is required for shared libraries")
        for path in glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True):
            if os.path.islink(path):
                continue
            pending = path + ".pending"
            shutil.copyfile(path, pending)
            if os.path.isfile(objcopy):
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", pending],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            self.run(
                '"{}" sign -selfSign 1 -inFile "{}" -outFile "{}"'.format(
                    signer, pending, path
                )
            )
            os.remove(pending)
            os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = ["include/geogram1"]
        self.cpp_info.libs = ["geogram"]
        self.cpp_info.set_property("cmake_file_name", "geogram")
        self.cpp_info.set_property("cmake_target_name", "geogram::geogram")
        self.cpp_info.set_property("pkg_config_name", "geogram")
        if self.settings.os != "Windows":
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
