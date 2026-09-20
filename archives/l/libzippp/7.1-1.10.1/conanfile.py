#!/usr/bin/env python3
"""Conan recipe — libzippp 7.1-1.10.1 (cmake)

libzippp: C++ wrapper for libzip. Upstream migrated from ctasada/libzippp
to ctabin/libzippp; tag libzippp-v7.1-1.10.1 targets libzip 1.10.x and
master tracks 1.11.4 (the W0-core version published in our registry).

Version scheme: upstream tag `libzippp-v7.1-1.10.1` maps to conan version
`7.1-1.10.1` (libzippp release 7.1 built against libzip 1.10.1).
"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches


class LibzipppConan(ConanFile):
    name = "libzippp"
    version = "7.1-1.10.1"
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

    def requirements(self):
        # W0: libzip 1.11.4 已发布制品仓（master 分支已跟进 1.11.4，本 tag 亦兼容）。
        # zlib 显式声明：上游 FindLIBZIP.cmake 内部 find_package(ZLIB REQUIRED) 直接找 ZLIB
        # 缓存变量，显式依赖后 conan 才会把 zlib 包 folder 交到 self.dependencies 里供预设。
        self.requires("libzip/1.11.4")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
        # ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
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
        # OHOS SDK 的 llvm/bin 下**只有 llvm-ar，没有 llvm-ranlib**，而 ohos.toolchain.cmake
        # 仍把 CMAKE_RANLIB 指过去。cmake 造静态库是 `<AR> qc ... && <RANLIB> <lib>`，
        # 于是 .o 全编得动、一造 .a 就 ENOENT。返回 "" 表示不覆盖（SDK 自带就用它的）。
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        # 让依赖能被 find_package 找到（FIND_ROOT_PATH=ONLY 交叉链阻断 sysroot 外搜索）。
        # CMAKE_PROJECT_TOP_LEVEL_INCLUDES 在 toolchain 之后、project() 之后、第一个
        # find_package 之前执行。无依赖时返回 ""，不写这个文件。
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
        # os=OHOS 下 conan_toolchain 把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值
        # （ML-0035）——同 libzip/1.11.4：自发现 ohos.toolchain + 裸 cmake。
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
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        _pre = self._find_deps_preload()
        if _pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(_pre))
        # libzippp 选项：只装库+头文件，关测试与加密（加密引 openssl 依赖链）
        defs.append("-DBUILD_SHARED_LIBS=ON")
        defs.append("-DLIBZIPPP_BUILD_TESTS=OFF")
        defs.append("-DLIBZIPPP_ENABLE_ENCRYPTION=OFF")
        defs.append("-DLIBZIPPP_GNUINSTALLDIRS=ON")
        defs.append("-DCMAKE_POLICY_VERSION_MINIMUM=3.5")
        # 依赖接线：上游 MODULE 模式 find_package(LIBZIP) 走自带的 cmake/FindLIBZIP.cmake，
        # 内部 find_path(LIBZIP_INCLUDE_DIR zip.h) + find_library(LIBZIP_LIBRARY zip) +
        # find_file(_libzip_pkgcfg libzip.pc)。预设 find 缓存变量为依赖真实路径，
        # 绕过交叉链 FIND_ROOT_PATH=ONLY 对 sysroot 外路径的阻断。
        libzip = self.dependencies["libzip"]
        libzip_inc = libzip.cpp_info.includedirs[0]
        libzip_lib = os.path.join(libzip.cpp_info.libdirs[0], "libzip.so")
        libzip_pcdir = os.path.join(libzip.cpp_info.libdirs[0], "pkgconfig")
        defs.append('-DLIBZIP_INCLUDE_DIR="{}"'.format(libzip_inc))
        defs.append('-DLIBZIP_LIBRARY="{}"'.format(libzip_lib))
        defs.append('-D_libzip_pkgcfg="{}"'.format(os.path.join(libzip_pcdir, "libzip.pc")))
        # FindLIBZIP.cmake 内部还有 find_package(ZLIB REQUIRED)——同法预设 ZLIB 缓存变量。
        # 交叉链下 CMake 内置 FindZLIB 会搜到不存在的相对路径（lib/libz.so + build include），
        # 必须 upfront 预设 ZLIB_INCLUDE_DIR/ZLIB_LIBRARY 为 conan zlib 包真实路径。
        # Requirement 对象：str(_r) 形如 'zlib/1.3.1.1'（无 .name 属性）。
        zlib = None
        for _r, _d in self.dependencies.items():
            if str(_r).split("/")[0] == "zlib":
                zlib = _d
                break
        if zlib is not None:
            zlib_inc = zlib.cpp_info.includedirs[0]
            for _cand in ("libz.so", "libz.a"):
                _p = os.path.join(zlib.cpp_info.libdirs[0], _cand)
                if os.path.exists(_p):
                    zlib_lib = _p
                    break
            else:
                zlib_lib = os.path.join(zlib.cpp_info.libdirs[0], "libz.so")
            defs.append('-DZLIB_INCLUDE_DIR="{}"'.format(zlib_inc))
            defs.append('-DZLIB_LIBRARY="{}"'.format(zlib_lib))
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
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名。
        import glob, os
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
        # 上游 set_target_properties(PREFIX "") 去重前缀 → 产物名 lib/libzippp.so（链接名 zippp）
        explicit_libs = ['zippp']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "libzippp")
        self.cpp_info.set_property("cmake_target_name", "libzippp::libzippp")
        pkg = "" or "libzippp"
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))
