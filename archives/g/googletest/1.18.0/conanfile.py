#!/usr/bin/env python3
"""Conan recipe for GoogleTest 1.18.0."""

import os
import glob
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


required_conan_version = ">=2.0"


class GoogletestConan(ConanFile):
    name = "googletest"
    version = "1.18.0"
    package_type = "library"

    description = "GoogleTest and GoogleMock C++ testing and mocking framework"
    homepage = "https://github.com/google/googletest"
    license = "BSD-3-Clause"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_CXX_STANDARD"] = "17"
        toolchain.variables["BUILD_GMOCK"] = True
        toolchain.variables["INSTALL_GTEST"] = True
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["gtest_build_tests"] = True
        toolchain.variables["gmock_build_tests"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            toolchain = self._ohos_toolchain()
            ranlib = self._ohos_ranlib()
            toolchain = self._ohos_toolchain_with_ranlib(toolchain, ranlib)
            build_dir = os.path.join(self.build_folder, "build-ohos")
            definitions = [
                '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
                '-DCMAKE_RANLIB="{}"'.format(ranlib),
                '-DCMAKE_C_COMPILER_RANLIB="{}"'.format(ranlib),
                '-DCMAKE_CXX_COMPILER_RANLIB="{}"'.format(ranlib),
                "-DOHOS_ARCH=arm64-v8a",
                "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
                "-DCMAKE_INSTALL_LIBDIR=lib",
                "-DBUILD_GMOCK=ON",
                "-DINSTALL_GTEST=ON",
                "-DBUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
                "-DCMAKE_CXX_STANDARD=17",
                "-Dgtest_build_tests=ON",
                "-Dgmock_build_tests=ON",
            ]
            self.run('cmake -G Ninja -S "{}" -B "{}" {}'.format(
                self.source_folder, build_dir, " ".join(definitions)))
            self.run('cmake --build "{}" --parallel 2'.format(build_dir))
            return
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _ohos_toolchain(self):
        configured = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain",
            default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(configured)
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake"))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        globbed = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：请设置 OHOS_NDK_HOME 或 "
            "tools.cmake.cmaketoolchain:user_toolchain")

    def _ohos_toolchain_with_ranlib(self, toolchain, ranlib):
        """Force ranlib variables after the SDK toolchain is included."""
        wrapper = os.path.join(self.build_folder, "ohos-toolchain-with-ranlib.cmake")
        toolchain_path = os.path.abspath(toolchain).replace("\\", "/").replace('"', '\\"')
        ranlib_path = os.path.abspath(ranlib).replace("\\", "/").replace('"', '\\"')
        with open(wrapper, "w", encoding="utf-8", newline="\n") as stream:
            stream.write('include("{}")\n'.format(toolchain_path))
            for variable in (
                "CMAKE_RANLIB",
                "CMAKE_C_COMPILER_RANLIB",
                "CMAKE_CXX_COMPILER_RANLIB",
            ):
                stream.write(
                    'set({} "{}" CACHE FILEPATH "" FORCE)\n'.format(
                        variable, ranlib_path))
        return wrapper

    def _ohos_ranlib(self):
        """Provide ranlib semantics when the OHOS SDK omits llvm-ranlib."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        compiler = executables.get("cpp") or executables.get("c")
        candidates = []
        if compiler:
            tool_dir = os.path.dirname(os.path.abspath(str(compiler)))
            candidates.extend(
                os.path.join(tool_dir, name) for name in ("llvm-ar", "llvm-ar.exe")
            )
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        if ndk:
            candidates.extend(
                os.path.join(ndk, "llvm", "bin", name)
                for name in ("llvm-ar", "llvm-ar.exe")
            )
        candidates.extend(
            os.path.join(root, "ohos", "native", "llvm", "bin", name)
            for root in glob.glob("/data/service/hnp/ohos-sdk.org/*")
            for name in ("llvm-ar", "llvm-ar.exe")
        )
        for name in ("llvm-ar", "llvm-ar.exe"):
            found = shutil.which(name)
            if found:
                candidates.append(found)
        ar = next((path for path in candidates if os.path.isfile(path)), None)
        if not ar:
            raise ConanInvalidConfiguration(
                "OHOS 静态归档需要 llvm-ar；未能从 compiler_executables 或 PATH 定位")
        if os.name != "posix":
            raise ConanInvalidConfiguration(
                "OHOS ranlib 兼容包装器需要 POSIX shell 环境")
        wrapper = os.path.join(self.build_folder, "ohos-ranlib")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("#!/bin/sh\nexec {} s \"$@\"\n".format(shlex.quote(ar)))
        os.chmod(wrapper, os.stat(wrapper).st_mode | 0o111)
        return wrapper

    def package(self):
        if self.settings.os == "OHOS":
            build_dir = os.path.join(self.build_folder, "build-ohos")
            self.run('cmake --install "{}" --prefix "{}"'.format(
                build_dir, self.package_folder))
            return
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GTest")

        gtest = self.cpp_info.components["gtest"]
        gtest.set_property("cmake_target_name", "GTest::gtest")
        gtest.set_property("pkg_config_name", "gtest")
        gtest.libs = ["gtest"]
        if self.settings.os in ("Linux", "OHOS"):
            gtest.system_libs = ["pthread"]

        gtest_main = self.cpp_info.components["gtest_main"]
        gtest_main.set_property("cmake_target_name", "GTest::gtest_main")
        gtest_main.set_property("pkg_config_name", "gtest_main")
        gtest_main.libs = ["gtest_main"]
        gtest_main.requires = ["gtest"]

        gmock = self.cpp_info.components["gmock"]
        gmock.set_property("cmake_target_name", "GTest::gmock")
        gmock.set_property("pkg_config_name", "gmock")
        gmock.libs = ["gmock"]
        gmock.requires = ["gtest"]

        gmock_main = self.cpp_info.components["gmock_main"]
        gmock_main.set_property("cmake_target_name", "GTest::gmock_main")
        gmock_main.set_property("pkg_config_name", "gmock_main")
        gmock_main.libs = ["gmock_main"]
        gmock_main.requires = ["gmock", "gtest"]
