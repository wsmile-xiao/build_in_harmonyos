#!/usr/bin/env python3
"""Conan recipe for gflags 2.2.2 (CMake)."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
)


class GflagsConan(ConanFile):
    name = "gflags"
    version = "2.2.2.1"
    description = "C++ command-line flag declaration and parsing library"
    license = "BSD-3-Clause"
    homepage = "https://gflags.github.io/gflags/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        os_name = str(self.settings.os)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("gflags is packaged for Linux/OHOS")
        if os_name == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("gflags supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # Windows is case-insensitive: upstream Bazel file BUILD conflicts with
        # cmake_layout()'s default build/ directory.
        self.folders.source = "."
        self.folders.build = "conan-build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if os.name == "nt":
            toolchain.generator = "Ninja"
        if str(self.settings.os) == "OHOS":
            toolchain.variables["OHOS_ARCH"] = "arm64-v8a"
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_STATIC_LIBS"] = (
            str(self.settings.os) == "OHOS" or not bool(self.options.shared)
        )
        toolchain.variables["INSTALL_STATIC_LIBS"] = not bool(self.options.shared)
        toolchain.variables["BUILD_gflags_LIB"] = True
        toolchain.variables["BUILD_gflags_nothreads_LIB"] = False
        toolchain.variables["BUILD_PACKAGING"] = False
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.variables["INSTALL_HEADERS"] = True
        toolchain.variables["REGISTER_INSTALL_PREFIX"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build(cli_args=["--parallel", "2"])
        if cross_building(self):
            self.output.info("cross-building: upstream test binaries compiled but not executed")
        else:
            cmake.ctest(cli_args=["--output-on-failure"])

    def package(self):
        CMake(self).install()
        rm(self, "gflags_completions.sh", os.path.join(self.package_folder, "bin"))
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        if not self.options.shared or str(self.settings.os) != "OHOS":
            return
        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            if cross_building(self):
                self.output.info("cross-building: target-only shared-library signing skipped")
                return
            raise ConanInvalidConfiguration("OHOS objcopy/signing tools not found on native host")
        for library in libraries:
            if os.path.islink(library):
                continue
            # llvm-objcopy accepts a missing .codesign section; real errors must fail.
            self.run(
                '{} --remove-section .codesign "{}"'.format(objcopy, library)
            )
            self.run(
                '{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                    signer, library, library
                )
            )

        self._set_soname_and_resign(['libgflags.so'])

    def _set_soname_and_resign(self, sonames):
        """给缺 SONAME 的 .so 补上 SONAME 并**重新签名**。

        为何需要：本包产物无 DT_SONAME。后果不在本包，而在**下游** ——
        CMake 默认按完整路径链接无 SONAME 的库，于是把构建机的 conan cache
        绝对路径写进下游的 DT_NEEDED，换机器即无法加载。
        制品仓已实测到三个因此损坏的包（fontconfig / poppler / tbb）。

        为何用 patchelf 而不改构建系统：本包的 .so 本来就是**无版本名**
        （libfoo.so，没有 libfoo.so.X 实体），SONAME 设成文件名本身即完全正确，
        与上游本意一致；换构建方式的收益一样而风险更高。
        （若包里存在版本化实体文件，则说明上游有 SOVERSION 意图，
          那种情况应改构建方式而非 patchelf —— 见 skill 的 references/soname-repair.md）

        为何必须重签：改动 ELF 会破坏链接器自签，鸿蒙 PC 的 XPM 会拒绝 dlopen
        （报 Permission denied / Operation not permitted）。
        顺序必须是 patchelf → 剥旧签名段 → 自签。
        """
        import os
        patchelf = "/data/service/hnp/bin/patchelf"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for name in sonames:
            f = os.path.join(self.package_folder, "lib", name)
            if not os.path.isfile(f) or os.path.islink(f):
                self.output.warning("补 SONAME：找不到 %s，跳过" % f)
                continue
            self.run('{pe} --set-soname "{n}" "{f}"'.format(pe=patchelf, n=name, f=f))
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=f))
            self.output.info("已设 SONAME=%s 并重签" % name)

    def package_info(self):
        self.cpp_info.libs = ["gflags"]
        self.cpp_info.set_property("cmake_file_name", "gflags")
        self.cpp_info.set_property("cmake_target_name", "gflags::gflags")
        self.cpp_info.set_property("pkg_config_name", "gflags")
