#!/usr/bin/env python3
"""Conan recipe — libxslt 1.1.45 (cmake)"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches
from conan.tools.cmake import cmake_layout


class LibxsltConan(ConanFile):
    name = "libxslt"
    version = "1.1.45"
    description = "libxslt: XSLT 1.0 processing library (based on libxml2)"
    license = "MIT"
    homepage = "https://gitlab.gnome.org/GNOME/libxslt"
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
        self.requires("libxml2/2.15.3")
        # crypto ON：EXSLT crypto 扩展依赖 libgcrypt（其自身再依赖 libgpg-error）。
        self.requires("libgcrypt/1.11.0")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
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

    def _lib(self, pkg, names):
        import glob
        for n in names:
            hit = glob.glob(os.path.join(pkg, "lib", n))
            if hit:
                return hit[0]
        return os.path.join(pkg, "lib", names[0])

    def build(self):
        # glfw 式：自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain（ML-0035）。
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        xml2 = self.dependencies["libxml2"].package_folder
        gcrypt = self.dependencies["libgcrypt"].package_folder
        gpgerr = self.dependencies["libgpg-error"].package_folder  # libgcrypt 的传递依赖（链接期要找到）
        gcrypt_lib = self._lib(gcrypt, ["libgcrypt.so", "libgcrypt.a"])
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DBUILD_SHARED_LIBS=ON",
            "-DLIBXSLT_WITH_CRYPTO=ON",            # EXSLT crypto（依赖 libgcrypt）
            "-DLIBXSLT_WITH_PYTHON=OFF",
            "-DLIBXSLT_WITH_PROGRAMS=OFF",         # 纯库，不建 xsltproc
            "-DLIBXSLT_WITH_TESTS=OFF",
            # find_package(LibXml2 CONFIG)：ohos.toolchain 用普通 set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE
            # ONLY) 覆盖命令行，令 config 搜索只在 sysroot → 找不到 conan 的 libxml2。直接设 LibXml2_DIR
            # 指向 config 目录，find_package 优先用 <Name>_DIR、跳过 FIND_ROOT_PATH 搜索。
            '-DLibXml2_DIR="{}"'.format(os.path.join(xml2, "lib", "cmake", "libxml2")),
            '-DCMAKE_PREFIX_PATH="{};{}"'.format(xml2, gcrypt),
            # FindGcrypt.cmake 用 find_path/find_library；预设缓存变量绕过交叉链 find 限制。
            # GCRYPT_INCLUDE_DIRS 成为 Gcrypt::Gcrypt 的 INTERFACE_INCLUDE：设成双目录列表——gcrypt.h 内含
            # gpg-error.h，crypto.c 编译须同时拿到 libgcrypt + libgpg-error 两个 include，否则报 not found。
            '-DGCRYPT_INCLUDE_DIRS="{};{}"'.format(
                os.path.join(gcrypt, "include"), os.path.join(gpgerr, "include")),
            '-DGCRYPT_LIBRARY_RELEASE="{}"'.format(gcrypt_lib),
        ])
        # 链接 libgcrypt.so 会牵出其 DT_NEEDED libgpg-error.so.0 → 链接期须能找到 libgpg-error 的 lib 目录。
        ldflags = "-L{} -L{} -Wl,-rpath-link,{} -Wl,-rpath-link,{}".format(
            os.path.join(gcrypt, "lib"), os.path.join(gpgerr, "lib"),
            os.path.join(gcrypt, "lib"), os.path.join(gpgerr, "lib"))
        os.environ["LDFLAGS"] = ldflags + " " + os.environ.get("LDFLAGS", "")
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, self.source_folder, defs))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
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
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        # libxslt + libexslt 两个库；libexslt 依赖 libxslt。
        self.cpp_info.libs = ["exslt", "xslt"]
        self.cpp_info.set_property("cmake_file_name", "LibXslt")
        self.cpp_info.set_property("cmake_target_name", "LibXslt::LibXslt")
        self.cpp_info.set_property("pkg_config_name", "libxslt")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
