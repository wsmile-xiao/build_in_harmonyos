#!/usr/bin/env python3
"""Conan recipe for jansson — CMake build system.

Jansson is a C library for encoding, decoding and manipulating JSON data.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class JanssonConan(ConanFile):
    name = "jansson"
    version = "2.15.1.1"
    description = "C library for encoding, decoding and manipulating JSON data"
    license = "MIT"
    homepage = "https://github.com/akheron/jansson"
    url = "https://github.com/akheron/jansson"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["JANSSON_BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        self._set_soname_and_resign(['libjansson.so'])

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
        self.cpp_info.libs = ["jansson"]
