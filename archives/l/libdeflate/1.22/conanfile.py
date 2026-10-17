#!/usr/bin/env python3
"""Conan recipe for libdeflate 1.22 on HarmonyOS."""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibdeflateConan(ConanFile):
    name = "libdeflate"
    version = "1.22"
    description = "Optimized DEFLATE/deflate/zlib/gzip compression library"
    license = "MIT"
    homepage = "https://github.com/ebiggers/libdeflate"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def test_requirements(self):
        self.test_requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        sdk_lib = self._sdk_llvm_libdir()
        if not sdk_lib:
            raise ConanInvalidConfiguration(
                "Cannot locate OHOS SDK llvm/lib containing libxml2.so.16"
            )
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        env.vars(self, scope="build").save_script("conanbuild_lld_runtime")

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or compilers.get("cpp")
        candidates = []
        if cc:
            try:
                resource_dir = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            compiler = os.path.realpath(cc)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _llvm_tools(self):
        ar = shutil.which("ar")
        ranlib = shutil.which("ranlib")
        if ar and ranlib:
            return ar, ranlib
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or compilers.get("cpp")
        if not cc:
            return "llvm-ar", "llvm-ranlib"
        tool_dir = os.path.dirname(os.path.realpath(cc))
        ar = os.path.join(tool_dir, "llvm-ar")
        ranlib = os.path.join(tool_dir, "llvm-ranlib")
        if not os.path.isfile(ranlib):
            ranlib = ar
        return ar, ranlib

    def _ohos_toolchain(self):
        user_toolchains = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list
        )
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(user_toolchains)
        if ndk:
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        candidates.extend(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"
            )
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain"
        )

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        build_dir = os.path.join(self.build_folder, "build-ohos")
        ar, ranlib = self._llvm_tools()
        cmake_args = [
            "-DCMAKE_TOOLCHAIN_FILE={}".format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_AR={}".format(ar),
            "-DCMAKE_RANLIB={}".format(ranlib),
            "-DLIBDEFLATE_BUILD_SHARED_LIB={}".format("ON" if self.options.shared else "OFF"),
            "-DLIBDEFLATE_BUILD_STATIC_LIB={}".format("OFF" if self.options.shared else "ON"),
            "-DLIBDEFLATE_BUILD_GZIP=OFF",
            "-DLIBDEFLATE_BUILD_TESTS=ON",
        ]
        cmake = "cmake -B \"{}\" -S \"{}\" {}".format(
            build_dir, self.source_folder, " ".join(cmake_args)
        )
        self.run(cmake, env="conanbuild")
        self.run('cmake --build "{}"'.format(build_dir), env="conanbuild")
        self.run('ctest --test-dir "{}" --output-on-failure'.format(build_dir), env="conanbuild")

    def package(self):
        build_dir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(build_dir, self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["deflate"]
        self.cpp_info.set_property("cmake_file_name", "libdeflate")
        self.cpp_info.set_property("cmake_target_name", "libdeflate::libdeflate")
        self.cpp_info.set_property("pkg_config_name", "libdeflate")
