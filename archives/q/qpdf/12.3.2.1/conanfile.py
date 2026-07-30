#!/usr/bin/env python3
"""Conan recipe — qpdf 12.3.2 (cmake)"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get
from conan.tools.cmake import CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class QpdfConan(ConanFile):
    name = "qpdf"
    version = "12.3.2.1"
    description = "qpdf: content-preserving PDF transformation library (C/C++ API)"
    license = "Apache-2.0"
    homepage = "https://github.com/qpdf/qpdf"
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
        # zlib 须用 1.3.1.1（-fPIC 静态库）：静态 libz.a 链进 libqpdf.so 时非 PIC 会报 R_AARCH64 relocation。
        self.requires("zlib/1.3.1.1")
        self.requires("libjpeg-turbo/3.2.0")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

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
        # qpdf 用 find_library(z)/find_path(zlib.h) + find_library(jpeg)/find_path(jpeglib.h)（非 find_package），
        # 故把依赖包目录喂给 CMAKE_PREFIX_PATH；又因 ohos.toolchain 是交叉链、默认 FIND_ROOT_PATH_MODE=ONLY
        # 只搜 sysroot，须把 LIBRARY/INCLUDE 的 find 模式设为 BOTH，find_library/find_path 才认 CMAKE_PREFIX_PATH。
        apply_conandata_patches(self)
        # 去掉 fuzz 子目录：oss-fuzz 模糊测试工具，库不需要，且其静态库归档在本环境链接失败（no such file）。
        # add_subdirectory(fuzz) 无条件，无 cmake 开关，直接 sed 掉。
        cml = os.path.join(self.source_folder, "CMakeLists.txt")
        _t = open(cml, encoding="utf-8").read()
        if "add_subdirectory(fuzz)" in _t:
            open(cml, "w", encoding="utf-8").write(
                _t.replace("add_subdirectory(fuzz)", "# add_subdirectory(fuzz)  # conan lib: 不编 fuzz"))
        toolchain = self._ohos_toolchain()
        import glob
        zlib_pkg = self.dependencies["zlib"].package_folder
        jpeg_pkg = self.dependencies["libjpeg-turbo"].package_folder
        # 直接定位依赖的真实头/库文件——预设 qpdf 的 find 缓存变量，绕开交叉链 FIND_ROOT_PATH_MODE=ONLY（toolchain
        # 把它设成 ONLY 覆盖了命令行，导致 find_path 只搜 sysroot、找不到 conan 依赖）。变量名对应 qpdf CMakeLists 里的
        # find_path/find_library 目标；已设则 find_* 直接用、不再搜索。
        def _lib(pkg, names):
            for n in names:
                hit = glob.glob(os.path.join(pkg, "lib", n))
                if hit:
                    return hit[0]
            return os.path.join(pkg, "lib", names[0])
        zlib_lib = _lib(zlib_pkg, ["libz.a", "libz.so"])
        jpeg_lib = _lib(jpeg_pkg, ["libjpeg.so", "libjpeg.a"])
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",          # ohos.toolchain 64 位默认 lib64/
            # pkg-config 会捞到 conan 依赖包里 prefix 烤死的坏 .pc（libjpeg-turbo 的 /opt/...、zlib 的 //include），关掉
            "-DPKG_CONFIG_USE_CMAKE_PREFIX_PATH=OFF",
            # 预设 qpdf find_path/find_library 的缓存变量为 conan 依赖真实路径（绕开 FIND_ROOT_PATH_MODE=ONLY）
            '-DZLIB_H_PATH="{}"'.format(os.path.join(zlib_pkg, "include")),
            '-DZLIB_LIB_PATH="{}"'.format(zlib_lib),
            '-DLIBJPEG_H_PATH="{}"'.format(os.path.join(jpeg_pkg, "include")),
            '-DLIBJPEG_LIB_PATH="{}"'.format(jpeg_lib),
            "-DBUILD_SHARED_LIBS=ON",
            "-DBUILD_STATIC_LIBS=OFF",
            "-DUSE_IMPLICIT_CRYPTO=ON",             # 用内置 native crypto，不依赖 openssl/gnutls
            "-DBUILD_DOC=OFF",
            "-DINSTALL_EXAMPLES=OFF",
            "-DINSTALL_MANUAL=OFF",
        ])
        # 清空 PKG_CONFIG_PATH：conan 依赖包的 .pc prefix 是烤死的错路径（libjpeg-turbo 的 /opt/...、zlib 的 //include），
        # qpdf 优先用 pkg_check_modules 一旦命中就拿到错 include（jpeglib.h not found）。清掉后 qpdf 回退 find_path/
        # find_library，走上面的 CMAKE_PREFIX_PATH（conan 包真实路径）。
        self.run('PKG_CONFIG_PATH= cmake -B "{}" -S "{}" {}'.format(bdir, self.source_folder, defs))
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
        # OHOS XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名（cmake/SDK-toolchain 产的自签无效，
        # 且 conan install 复制会破坏自签）。① lib/ 的 .so（libqpdf.so）② bin/ 的 ELF（qpdf/zlib-flate/fix-qdf）。
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
        explicit_libs = ['qpdf']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "qpdf")
        self.cpp_info.set_property("cmake_target_name", "qpdf::libqpdf")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        import glob
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
