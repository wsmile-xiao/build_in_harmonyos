#!/usr/bin/env python3
"""Conan recipe — zstd 1.5.6 (cmake)"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get
from conan.tools.cmake import CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class ZstdConan(ConanFile):
    name = "zstd"
    version = "1.5.6"
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
        import os
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        sdk_base = os.environ.get("OHOS_SDK_HOME", "/data/service/hnp/ohos-sdk.org")
        globbed = sorted(glob.glob(os.path.join(sdk_base, "*", "ohos", "native", "build", "cmake", "ohos.toolchain.cmake")))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 OHOS_SDK_HOME，或在 profile [conf] 配 "
            "tools.cmake.cmaketoolchain:user_toolchain=[<sdk>/ohos/native/build/cmake/ohos.toolchain.cmake]")

    def _prepare_env(self):
        # lld 链接器依赖 libxml2.so.16，但 CI worker 的系统库路径未包含该库。
        # SDK 的 llvm/lib 目录包含 libxml2.so.16，将其加入 LD_LIBRARY_PATH。
        # 与 openblas/0.3.34、wolfssl/5.9.0 等已发布 recipe 同法（知识图谱 E120/E132）。
        import os
        import glob
        sdk_llvm_lib = ""
        sdk_base = os.environ.get("OHOS_SDK_HOME", "/data/service/hnp/ohos-sdk.org")
        g = sorted(glob.glob(os.path.join(sdk_base, "*", "ohos", "native", "llvm", "lib")))
        if g:
            sdk_llvm_lib = g[-1]
        if sdk_llvm_lib:
            old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = sdk_llvm_lib + (os.pathsep + old if old else "")

    def build(self):
        import os
        self._prepare_env()
        apply_conandata_patches(self)
        self._patch_gnu_qsort_r()
        toolchain = self._ohos_toolchain()
        cml_dir = os.path.join(self.source_folder, "build", "cmake")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",  # ohos.toolchain.cmake 的目标架构；与 1.5.7 一致，OHOS PC 当前仅 arm64
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DZSTD_BUILD_SHARED=ON",
            "-DZSTD_BUILD_STATIC=OFF",
            "-DZSTD_BUILD_PROGRAMS=OFF",
            "-DZSTD_BUILD_TESTS=OFF",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, cml_dir, defs))
        self.run('cmake --build "{}"'.format(bdir))

    def _patch_gnu_qsort_r(self):
        # zstd 1.5.6 源码中不包含 qsort_r 相关守卫（上游在 1.5.6 移除了 GNU qsort_r 路径），
        # 此方法为 no-op。保留方法体以兼容 1.5.7 recipe 结构，CI 日志中 warning 属预期行为。
        # 若上游在后续版本重新引入 qsort_r 守卫，此处会自动补丁（模式与 1.5.7 一致）。
        import os
        old = "#if !defined(_GNU_SOURCE) && !defined(__ANDROID__)"
        new = "#if !defined(_GNU_SOURCE) && !defined(__ANDROID__) && !defined(__OHOS__)"
        for rel in ("lib/dictBuilder/cover.c", "lib/common/zstd_deps.h"):
            p = os.path.join(self.source_folder, rel)
            if not os.path.isfile(p):
                continue
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
        import glob
        import os
        import shutil
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = os.environ.get("OHOS_OBJCOPY") or shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = os.environ.get("OHOS_SIGN_TOOL") or shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
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
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]