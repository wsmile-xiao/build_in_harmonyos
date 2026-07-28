#!/usr/bin/env python3
"""Conan recipe — poppler 25.12.0.1 (CMake).

PDF rendering library providing PDF document processing functionality.

25.12.0.1 相对 25.12.0 的改动（**仅构建方式，源码补丁与功能面不变**）：
改用「自发现 SDK ohos.toolchain + 裸 cmake」，替代 conan 的 CMakeToolchain/CMake(self)。
25.12.0 用后者时，os=OHOS 下 CMAKE_SYSTEM_NAME 被映射成 cmake 不认的 HarmonyOS（ML-0035），
导致产出的 .so **既无 SONAME 也无版本软链**——poppler 自己明明设了
SOVERSION（poppler=155、poppler-cpp=2），全被丢掉。后果是 libpoppler-cpp.so 的 DT_NEEDED
变成相对路径 `../libpoppler.so`（加载器按进程 CWD 解析，基本不可能命中）。
同时补上 ELF 代码签名（cmake install 是复制、会破坏链接器自签，bin/ 下 11 个 CLI 工具需要）。

Patches: 39 patches fixing C++23 std::ranges compatibility (adding std:: prefix) + iconv 可选化
Dependencies: freetype, zlib；fontconfig 经 FONT_CONFIGURATION=generic 绕开
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout
from conan.errors import ConanInvalidConfiguration
import os


class PopplerConan(ConanFile):
    name = "poppler"
    version = "25.12.0.1"
    package_type = "library"
    description = "PDF rendering library providing PDF document processing functionality"
    license = "GPL-2.0-or-later"
    homepage = "https://poppler.freedesktop.org/"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("freetype/2.14.3")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ 工具

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

    _HNP_BIN = "/data/service/hnp/bin"

    def _tool(self, name):
        # SDK 的 llvm/bin 只有 llvm-ar、没有 llvm-ranlib，而 ohos.toolchain 会把 CMAKE_RANLIB
        # 指到那个不存在的路径 → 造静态库时报 "Error running link command: no such file or
        # directory"。hnp bin 下的 llvm-ranlib 是指向 llvm-ar 的软链（LLVM 按 argv[0] 改行为）。
        import shutil
        cand = os.path.join(self._HNP_BIN, name)
        if os.path.isfile(cand) or os.path.islink(cand):
            return cand
        return shutil.which(name) or ""

    def _dep(self, name):
        return self.dependencies[name].package_folder

    def _dep_lib(self, name, *stems):
        """在依赖包 lib/ 下找库文件，优先 .so 再 .a——制品仓里 zlib 按 R26 是静态、
        freetype 是动态，硬编码后缀会随依赖形态变化而断。"""
        import glob
        libdir = os.path.join(self._dep(name), "lib")
        for stem in stems:
            for pat in ("lib%s.so" % stem, "lib%s.a" % stem):
                hit = sorted(glob.glob(os.path.join(libdir, pat)))
                if hit:
                    return hit[0]
        raise ConanInvalidConfiguration(
            "依赖 %s 的 lib/ 下找不到 %s 的 .so/.a：%s" % (name, "/".join(stems), libdir))

    def _freetype_incdir(self):
        """FindFreetype 要 ft2build.h 所在目录；本仓 freetype 包把头装在 include/freetype2/。"""
        base = os.path.join(self._dep("freetype"), "include")
        for cand in (os.path.join(base, "freetype2"), base):
            if os.path.isfile(os.path.join(cand, "ft2build.h")):
                return cand
        return os.path.join(base, "freetype2")

    # ------------------------------------------------------------------ 构建

    def _configure_defs(self):
        ft_inc = self._freetype_incdir()
        d = [
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % self._ohos_toolchain(),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            "-DCMAKE_INSTALL_LIBDIR=lib",     # ohos.toolchain 64 位默认 lib64/，conan 找 lib/
            "-DBUILD_SHARED_LIBS=%s" % ("ON" if self.options.shared else "OFF"),
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            # 注意：**不设 CMAKE_CXX_STANDARD**。poppler 自己 set(CMAKE_CXX_STANDARD 23)，
            # 那 39 个补丁正是为补 clang 15 的 C++23 缺口而存在，覆盖它会让补丁失去前提。
        ]
        for _var, _name in (("CMAKE_RANLIB", "llvm-ranlib"), ("CMAKE_AR", "llvm-ar")):
            _p = self._tool(_name)
            if _p:
                d.append('-D%s="%s"' % (_var, _p))

        # 依赖接线：交叉 toolchain 在文件里 set(CMAKE_FIND_ROOT_PATH_MODE_* ONLY)，会覆盖命令行的
        # BOTH，find_package(Freetype/ZLIB) 搜不到 conan 依赖 → 直接预设各 Find 模块的结果缓存变量。
        # poppler 用的是 imported target（Freetype::Freetype / ZLIB::ZLIB），这些 target 由
        # FindFreetype/FindZLIB 依据下列变量生成，预设即可。
        d += [
            '-DFREETYPE_LIBRARY="%s"' % self._dep_lib("freetype", "freetype"),
            '-DFREETYPE_INCLUDE_DIR_ft2build="%s"' % ft_inc,
            '-DFREETYPE_INCLUDE_DIR_freetype2="%s"' % ft_inc,
            '-DZLIB_LIBRARY="%s"' % self._dep_lib("zlib", "z"),
            '-DZLIB_INCLUDE_DIR="%s"' % os.path.join(self._dep("zlib"), "include"),
        ]

        # 与 25.12.0 完全一致的功能开关（本次只改构建方式，不改功能面）
        d += [
            "-DFONT_CONFIGURATION=generic",   # 不依赖 fontconfig
            "-DENABLE_BOOST=OFF",
            "-DENABLE_CPP=ON",
            "-DENABLE_GLIB=OFF",
            "-DENABLE_GOBJECT_INTROSPECTION=OFF",
            "-DENABLE_GTK_DOC=OFF",
            "-DENABLE_QT5=OFF",
            "-DENABLE_QT6=OFF",
            "-DENABLE_UNSTABLE_API_ABI_HEADERS=ON",
            "-DENABLE_NSS3=OFF",
            "-DENABLE_GPGME=OFF",
            "-DENABLE_LIBCURL=OFF",
            "-DENABLE_LIBTIFF=OFF",
            "-DENABLE_DCTDECODER=none",
            "-DENABLE_LIBOPENJPEG=none",
            "-DENABLE_LCMS=OFF",
            "-DBUILD_GTK_TESTS=OFF",
            "-DBUILD_QT5_TESTS=OFF",
            "-DBUILD_QT6_TESTS=OFF",
            "-DBUILD_CPP_TESTS=OFF",
            "-DBUILD_MANUAL_TESTS=OFF",
        ]
        roots = ";".join(self._dep(n) for n in ("freetype", "zlib"))
        d += ['-DCMAKE_FIND_ROOT_PATH="%s"' % roots, '-DCMAKE_PREFIX_PATH="%s"' % roots]
        return d

    def build(self):
        apply_conandata_patches(self)
        # 设备 HiShell 的 .zshrc 会全局导出这些，会漏进 cmake（链错库 / find_package 捞到 ~/usr/local）
        for _v in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS",
                   "PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR", "CMAKE_PREFIX_PATH", "LD_LIBRARY_PATH"):
            os.environ.pop(_v, None)
        _tmp = os.path.join(self.build_folder, "_tmp")     # HMDFS 默认 TMPDIR 不可写
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        bdir = os.path.join(self.build_folder, "build-ohos")
        jobs = self.conf.get("tools.build:jobs", default=os.cpu_count() or 4, check_type=int)
        self.run('cmake -B "{b}" -S "{s}" {d}'.format(
            b=bdir, s=self.source_folder, d=" ".join(self._configure_defs())))
        self.run('cmake --build "{b}" -j {j}'.format(b=bdir, j=jobs))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "%s" --prefix "%s"' % (bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 对 dlopen 的 .so 与被 exec 的可执行文件都校验代码签名。
        # cmake install 是复制、不重链 → 破坏链接器自签；25.12.0 缺这一步。
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
            if os.path.islink(f):     # 只签真实 ELF，跳版本化 .so 的软链
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["poppler-cpp", "poppler"]   # 上层在前：poppler-cpp 依赖 poppler
        self.cpp_info.includedirs = ["include", "include/poppler"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "poppler")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
