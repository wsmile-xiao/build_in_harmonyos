#!/usr/bin/env python3
"""Conan recipe — libvncserver 0.9.15 (cmake)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class LibvncserverConan(ConanFile):
    name = "libvncserver"
    version = "0.9.15"
    description = "A library for easy implementation of a VNC server and client."
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/LibVNC/libvncserver"
    url = "https://github.com/LibVNC/libvncserver"
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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("lzo/2.10")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng/1.6.58")
        self.requires("openssl/3.5.6")

    def layout(self):
        from conan.tools.cmake import cmake_layout
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain
        # ② 环境 OHOS_NDK_HOME ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        # 让依赖能被 find_package 找到。不能靠 -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH：
        # ohos.toolchain 用普通 set()（非 CACHE）设了 ONLY，普通变量盖得住命令行 cache 变量。
        import os
        deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        if not deps:
            return ""
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8") as f:
            for d in deps:
                p = d.replace("\\", "/")
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DBUILD_SHARED_LIBS=ON" if self.options.shared else "-DBUILD_SHARED_LIBS=OFF",
            # 上游 CMakeLists.txt 声明 cmake_minimum_required(VERSION 3.4)，而本机 CMake 4.x
            # 已移除对 <3.5 的兼容，直接 configure 报错。用策略最小版本下限跳过该检查。
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        _pre = self._find_deps_preload()
        if _pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(_pre))
        # 组件开关：启用已发布依赖对应的编码/传输特性
        defs.append("-DWITH_ZLIB=ON")
        defs.append("-DWITH_LZO=ON")
        defs.append("-DWITH_JPEG=ON")
        defs.append("-DWITH_PNG=ON")
        defs.append("-DWITH_OPENSSL=ON")
        defs.append("-DWITH_GNUTLS=OFF")
        defs.append("-DWITH_GCRYPT=OFF")
        # sasl 未在 ohpcd 发布 → 关闭，避免依赖不可达
        defs.append("-DWITH_SASL=OFF")
        # 不需要的示例/客户端框架依赖全部关闭
        defs.append("-DWITH_SDL=OFF")
        defs.append("-DWITH_GTK=OFF")
        defs.append("-DWITH_LIBSSHTUNNEL=OFF")
        defs.append("-DWITH_FFMPEG=OFF")
        defs.append("-DWITH_QT=OFF")
        defs.append("-DWITH_XCB=OFF")
        defs.append("-DWITH_SYSTEMD=OFF")
        # 上游测试在 test_package/本地验证中单独执行，配方内不构建
        defs.append("-DWITH_EXAMPLES=OFF")
        defs.append("-DWITH_TESTS=OFF")
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.components["vncserver"].libs = ["vncserver"]
        self.cpp_info.components["vncclient"].libs = ["vncclient"]
        self.cpp_info.set_property("cmake_file_name", "LibVNCServer")
        self.cpp_info.components["vncserver"].set_property(
            "cmake_target_name", "LibVNCServer::vncserver")
        self.cpp_info.components["vncclient"].set_property(
            "cmake_target_name", "LibVNCServer::vncclient")
