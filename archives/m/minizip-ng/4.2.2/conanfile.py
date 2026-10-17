#!/usr/bin/env python3
"""Conan recipe — minizip-ng 4.2.2 (cmake, C)

minizip-ng: zip manipulation library (modern rewrite of minizip from
zlib-contrib). Version follow-up of the archived 4.1.1 (autotools era
record, no conan recipe on main).

Dependency surface: zlib (compression core) + openssl (crypt) + bzip2 +
zstd, matching the upstream default feature set so the gtest suite runs
unabridged. LZMA/PPMD off (no xz_utils/lzma-sdk packages in registry).
"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches


class MinizipNgConan(ConanFile):
    name = "minizip-ng"
    version = "4.2.2"
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
        # W0: all published in the registry
        self.requires("zlib/1.3.1.1")
        self.requires("openssl/3.5.6.1.2")
        self.requires("bzip2/1.0.8.2")
        self.requires("zstd/1.5.7")

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
        # OHOS SDK 的 llvm/bin 下只有 llvm-ar，ohos.toolchain.cmake 仍把 CMAKE_RANLIB 指过去。
        # 返回 "" 表示不覆盖（SDK 自带就用它的）。
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        # 让依赖能被 find_package 找到（FIND_ROOT_PATH=ONLY 交叉链阻断 sysroot 外搜索）。
        # CMAKE_PROJECT_TOP_LEVEL_INCLUDES 在 toolchain 之后、project() 之后、第一个
        # find_package 之前执行。无依赖时返回 ""。
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
        defs.append("-DBUILD_SHARED_LIBS=ON")
        # 依赖接线：上游 find_package(ZLIB/LibLZMA/OpenSSL/zstd/BZip2)。交叉链
        # FIND_ROOT_PATH=ONLY 下需给每个依赖预设 config 路径（cmake config 目录）。
        for dep_name, cmake_dir in (("zlib", "zlib"),
                                    ("openssl", "OpenSSL"),
                                    ("bzip2", "bzip2"),
                                    ("zstd", "zstd")):
            dep = self.dependencies.get(dep_name)
            if dep is None:
                continue
            pkg = dep.package_folder
            libcm = os.path.join(pkg, "lib", "cmake")
            for _sub in (cmake_dir, cmake_dir.lower(), cmake_dir.upper()):
                if os.path.isdir(os.path.join(libcm, _sub)):
                    defs.append('-D{}_DIR="{}"'.format(_sub, os.path.join(libcm, _sub)))
                    break
            else:
                if os.path.isdir(libcm):
                    # 兜底：openssl 的 config 在 lib/cmake/OpenSSL
                    for ent in os.listdir(libcm):
                        if cmake_dir.lower() in ent.lower():
                            defs.append('-D{}_DIR="{}"'.format(ent, os.path.join(libcm, ent)))
                            break
        # 功能面：zlib+openssl+bzip2+zstd 开，lzma/ppmd 关（registry 无 xz/lzma-sdk 包）
        defs.append("-DMZ_ZLIB=ON")
        defs.append("-DMZ_BZIP2=ON")
        defs.append("-DMZ_ZSTD=ON")
        defs.append("-DMZ_LZMA=OFF")
        defs.append("-DMZ_PPMD=OFF")
        defs.append("-DMZ_OPENSSL=ON")
        defs.append("-DMZ_FETCH_LIBS=OFF")
        defs.append("-DMZ_BUILD_TESTS=OFF")
        defs.append("-DMZ_BUILD_UNIT_TESTS=OFF")
        defs.append("-DMZ_BUILD_FUZZ_TESTS=OFF")
        defs.append("-DMZ_ICONV=OFF")               # musl 无 iconv，上游按平台宏退化
        defs.append("-DMZ_LIBBSD=OFF")              # 避免 find_package(libbsd) 交叉乱猜
        defs.append("-DCMAKE_POLICY_VERSION_MINIMUM=3.5")
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
        explicit_libs = ['minizip']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "minizip")
        self.cpp_info.set_property("cmake_target_name", "minizip::minizip")
        pkg = "" or "minizip"
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))
