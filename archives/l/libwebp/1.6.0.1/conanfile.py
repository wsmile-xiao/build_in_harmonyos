#!/usr/bin/env python3
"""Conan recipe — libwebp 1.6.0.1 (cmake)"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get
from conan.tools.cmake import CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class LibwebpConan(ConanFile):
    name = "libwebp"
    version = "1.6.0.1"
    description = "WebP image codec library (encode/decode)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/webmproject/libwebp"
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
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（不依赖 profile host 段 user_toolchain）。
        import glob
        import os
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

    def _hmdfs_no_symlink(self):
        # HMDFS 禁止 symlink（ln -s EPERM）。libwebp 构建产 libwebp.so.7 → libwebp.so 软链，
        # 若文件系统不支持 symlink 则改单文件名（无版本化 soname，E492 同类）。
        import os
        probe = os.path.join(self.build_folder, "probe.lnk")
        try:
            os.symlink("x", probe)
            os.remove(probe)
            return False
        except OSError:
            return True

    def build(self):
        # glfw/libjpeg-turbo/zstd/libtiff 同法：自发现 ohos.toolchain + 裸 cmake，
        # 绕开 conan_toolchain（ML-0035）。
        import os
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",   # ohos.toolchain 64 位默认 lib64/，强制 lib/
            "-DBUILD_SHARED_LIBS=ON",
            "-DWEBP_BUILD_CWEBP=OFF",       # 不编命令行工具，仅库本体
            "-DWEBP_BUILD_DWEBP=OFF",
            "-DWEBP_BUILD_GIF2WEBP=OFF",
            "-DWEBP_BUILD_IMG2WEBP=OFF",
            "-DWEBP_BUILD_VWEBP=OFF",
            "-DWEBP_BUILD_WEBPINFO=OFF",
            "-DWEBP_BUILD_WEBPMUX=OFF",
            "-DWEBP_BUILD_ANIM_UTILS=OFF",
            "-DWEBP_BUILD_EXTRAS=OFF",
        ]
        if self._hmdfs_no_symlink():
            defs.append("-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON")
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, self.source_folder, " ".join(defs)))
        # 真机 make -jN 静默失败/吃满进程配额 → cmake --build --parallel 8。
        self.run('cmake --build "{}" --parallel 8'.format(bdir))

    def package(self):
        import os
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # cmake/SDK-toolchain 产的 .so 自签无效 → 剥旧 .codesign + binary-sign-tool -selfSign 重签。
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
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        # libwebp.so 链接 libsharpyuv.so，两者都要暴露。
        explicit_libs = ['webp', 'sharpyuv']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "WebP")
        self.cpp_info.set_property("cmake_target_name", "WebP::webp")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "libwebp.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
