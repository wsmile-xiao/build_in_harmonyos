#!/usr/bin/env python3
"""Conan recipe — libjpeg-turbo 3.0.4 (cmake)"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, export_conandata_patches, get
from conan.tools.cmake import CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class LibjpegTurboConan(ConanFile):
    name = "libjpeg-turbo"
    version = "3.0.4"
    description = "JPEG image codec with SIMD-capable baseline compression/decompression"
    license = "IJG AND BSD-3-Clause AND Zlib"
    homepage = "https://libjpeg-turbo.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（不依赖 profile host 段有没有 user_toolchain）：
        # ① profile [conf] 已配就用；② 环境 OHOS_NDK_HOME；③ glob 设备/CI 的 SDK 布局。
        import os
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME，或在 profile [conf] 配 "
            "tools.cmake.cmaketoolchain:user_toolchain=[<sdk>/ohos/native/build/cmake/ohos.toolchain.cmake]")

    def build(self):
        # 直接用 OHOS NDK 的 ohos.toolchain.cmake（CMAKE_SYSTEM_NAME=OHOS + 平台模块 → cmake 认识系统、
        # 正常出 SONAME/版本软链、GNUInstallDirs 不崩），而非 conan_toolchain——后者 os=OHOS 会退化成未知平台
        # HarmonyOS：cmake 报 "System is unknown"，且 libjpeg-turbo 旧 vendored GNUInstallDirs 的
        # set_property(CACHE CMAKE_INSTALL_*) 找不到 CACHE 项而失败（ML-0035）。自发现 toolchain 使 recipe
        # 自包含、不依赖 CI profile 的 host 段（与 glfw/3.4.6 同法）。
        import os
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",  # ohos.toolchain 在 64 位默认装 lib64/，须强制 lib/ 与 conan cpp_info 一致
            "-DENABLE_SHARED=ON",
            "-DENABLE_STATIC=OFF",     # 只出共享库
            "-DWITH_TOOLS=OFF",        # 不编 cjpeg/djpeg/jpegtran
            "-DWITH_TESTS=OFF",        # 跳过上游回归测试构建
            "-DWITH_SIMD=OFF",         # E096：OHOS 上 SIMD 链接失败，须禁（沿用 2.1.5.1/3.1.4.1 结论）
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, self.source_folder, defs))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        import os
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # 鸿蒙 PC 对 dlopen 的 .so 校验代码签名。真机实测：经 SDK toolchain 构建的 .so 自签可能无效
        # （dlopen 报 Permission denied）→ 剥旧 .codesign + binary-sign-tool -selfSign 1 重签（ML-0043）。
        import glob
        import os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue  # 只签真实 ELF，跳过软链
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        explicit_libs = ['jpeg', 'turbojpeg']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "libjpeg-turbo")
        self.cpp_info.set_property("cmake_target_name", "libjpeg-turbo::libjpeg-turbo")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        # 从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
