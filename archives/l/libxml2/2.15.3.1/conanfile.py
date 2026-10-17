#!/usr/bin/env python3
"""Conan recipe — libxml2 2.15.3.1 (cmake)"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class Libxml2Conan(ConanFile):
    name = "libxml2"
    version = "2.15.3.1"
    description = "libxml2: XML C parser and toolkit"
    license = "MIT"
    homepage = "https://gitlab.gnome.org/GNOME/libxml2"
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

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 默认 LIBXML2_WITH_ZLIB/LZMA=OFF（上游默认）；ICONV 走 musl libc 内建，无 conan 依赖。
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（不依赖 profile host 段 user_toolchain）。
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def build(self):
        # glfw/libjpeg-turbo/zstd 同法：自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain（ML-0035）。
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",          # ohos.toolchain 64 位默认 lib64/
            "-DBUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            # 规则4：接入上游测试套件（runtest 等 11 个测试程序 + ctest），实跑给出真实通过率。
            # CMake 的 add_suite()/catalog 测试无条件引用 xmllint/xmlcatalog 目标，
            # 因此 TESTS=ON 时必须同时 PROGRAMS=ON（否则生成阶段报 Target not found）。
            "-DLIBXML2_WITH_TESTS=ON",
            "-DLIBXML2_WITH_PROGRAMS=ON",          # 测试套件依赖 xmllint/xmlcatalog 目标
            "-DLIBXML2_WITH_PYTHON=OFF",
            "-DLIBXML2_WITH_ZLIB=OFF",             # 上游默认 OFF（避免拖 zlib 依赖）
            "-DLIBXML2_WITH_LZMA=OFF",             # 上游默认 OFF
            "-DLIBXML2_WITH_ICONV=ON",             # iconv 在 musl libc 内建
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, self.source_folder, defs))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # cmake/SDK-toolchain 产的 .so 自签无效 → 剥旧 .codesign + binary-sign-tool -selfSign 重签。
        import glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
            # 无 .codesign 段时 objcopy 报错可忽略
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ['xml2']
        self.cpp_info.set_property("cmake_file_name", "LibXml2")
        self.cpp_info.set_property("cmake_target_name", "LibXml2::LibXml2")
        self.cpp_info.set_property("pkg_config_name", "libxml-2.0")
        # libxml2 头装在 <pkg>/include/libxml2/libxml/*.h。双根：include/libxml2 供消费者 <libxml/x.h>
        # （libxslt 等惯用），include 供 <libxml2/libxml/x.h>（test_package 及部分消费者）。
        self.cpp_info.includedirs = ["include/libxml2", "include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
