#!/usr/bin/env python3
"""Conan recipe — zstd 1.5.7 (cmake)"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get
from conan.tools.cmake import CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class ZstdConan(ConanFile):
    name = "zstd"
    version = "1.5.7"
    description = "Zstandard - fast real-time compression algorithm"
    license = "BSD-3-Clause AND GPL-2.0-or-later"
    homepage = "https://github.com/facebook/zstd"
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
        # 正常出 SONAME/版本软链、GNUInstallDirs 不崩），而非 conan_toolchain（os=OHOS 退化成未知平台
        # HarmonyOS → cmake 报 "System is unknown"，ML-0035）。自发现 toolchain 使 recipe 自包含、不依赖
        # CI profile 的 host 段（与 glfw/3.4.6、libjpeg-turbo/3.2.0 同法）。
        import os
        apply_conandata_patches(self)
        self._patch_gnu_qsort_r()
        toolchain = self._ohos_toolchain()
        # zstd 的 CMakeLists 在 build/cmake 子目录
        cml_dir = os.path.join(self.source_folder, "build", "cmake")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",  # ohos.toolchain 64 位默认装 lib64/，须强制 lib/ 与 conan cpp_info 一致
            "-DZSTD_BUILD_SHARED=ON",
            "-DZSTD_BUILD_STATIC=OFF",     # 只出共享库
            "-DZSTD_BUILD_PROGRAMS=OFF",   # 不编 zstd/unzstd/zstdcat 命令行
            "-DZSTD_BUILD_TESTS=OFF",      # 跳过上游测试构建
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, cml_dir, defs))
        self.run('cmake --build "{}"'.format(bdir))

    def _patch_gnu_qsort_r(self):
        # OHOS 用 musl，无 GNU qsort_r。zstd 的 cover.c / zstd_deps.h 在 __linux__ 下自动 #define _GNU_SOURCE
        # → 走 glibc qsort_r → 链接期 undefined symbol: qsort_r。加 __OHOS__ 例外（同上游对 __ANDROID__ 的处理，
        # 注释即 "NDK doesn't ship qsort_r()"），令其走 C90 fallback（全局 ctx + 普通 qsort）。
        import os
        old = "#if !defined(_GNU_SOURCE) && !defined(__ANDROID__)"
        new = "#if !defined(_GNU_SOURCE) && !defined(__ANDROID__) && !defined(__OHOS__)"
        for rel in ("lib/dictBuilder/cover.c", "lib/common/zstd_deps.h"):
            p = os.path.join(self.source_folder, rel)
            with open(p, encoding="utf-8") as f:
                txt = f.read()
            if old in txt:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(txt.replace(old, new))

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
        explicit_libs = ['zstd']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "zstd")
        self.cpp_info.set_property("cmake_target_name", "zstd::libzstd")
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
