#!/usr/bin/env python3
"""Conan recipe — libpano13 2.9.23 (cmake)

Panorama Tools 全景拼接库。上游 2.9.23 已从 autotools 迁移到 CMake 构建。
必需依赖：libtiff / libjpeg(-turbo) / libpng / zlib（CMakeLists FIND_PACKAGE REQUIRED）。
可选依赖（默认 OFF，不启用）：
  - SUPPORT_JAVA_PROGRAMS（Java/JNI GUI 程序 ptpicker/pteditor）
  - USE_SPARSE_LEVMAR（SuiteSparse 稀疏 LM 算法）
  - PTDialogs 的 GIMP/GTK/X11 GUI 分支（无 GUI 环境走 __Ansi__ 纯 ANSI 分支）
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Libpano13Conan(ConanFile):
    name = "libpano13"
    version = "2.9.23"
    description = "libpano13 - Panorama Tools: the cross-platform library behind the Hugin photo stitcher"
    license = "GPL-2.0-or-later"
    homepage = "https://panotools.sourceforge.net/"
    url = "https://sourceforge.net/projects/panotools/files/libpano13/libpano13-2.9.23/"

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

    def requirements(self):
        # CMakeLists FIND_PACKAGE(TIFF/JPEG/PNG REQUIRED)：TIFF 4.7.2 已带全
        # zlib/libjpeg-turbo/zstd/libwebp 等传递依赖，此处按直接使用面显式声明。
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        self.requires("libtiff/4.7.2")
        self.requires("libjpeg-turbo/3.2.0")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
        # ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
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

    def build(self):
        # 裸 cmake + ohos.toolchain：绕开 conan_toolchain（os=OHOS 下它把 CMAKE_SYSTEM_NAME 映射成
        # cmake 不认的值，报 "System is unknown to cmake"）。与 libtiff/libjpeg-turbo 同法。
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            # PTDialogs.c 在非 __Ansi__ 分支 include sys_X11.h（libgimp/gimp.h + gtk/gtk.h），
            # 无 GUI 环境必须走 __Ansi__ 纯 ANSI 分支。CMakeLists 的 IF(UNIX) 在 OHOS 上
            # 不生效（cmake 不识别 HarmonyOS 平台），故经 CMAKE_C_FLAGS 显式注入。
            "-DCMAKE_C_FLAGS=-D__Ansi__",
            "-DSUPPORT_JAVA_PROGRAMS=OFF",
            "-DUSE_SPARSE_LEVMAR=OFF",
        ]
        # OHOS SDK 的 llvm/bin/ 只有 llvm-ar、无 llvm-ranlib；ohos.toolchain 将 CMAKE_RANLIB
        # 指向 SDK 内不存在的 llvm-ranlib → libpano13a 静态库归档 "no such file or directory"。
        # 显式重指到实际存在的 ranlib（默认 /data/service/hnp/bin/llvm-ranlib 软链 → llvm-ar，
        # 可用环境变量 OHOS_LLVM_RANLIB 覆盖）。
        _ranlib = next((p for p in (
            os.environ.get("OHOS_LLVM_RANLIB", ""),
            "/data/service/hnp/bin/llvm-ranlib",
            os.path.join(os.path.dirname(toolchain), "../../native/llvm/bin/llvm-ranlib"),
        ) if p and os.path.exists(p)), None)
        if _ranlib:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_ranlib))
        # 依赖接线：libpano13 用 CMake 内置 FIND_PACKAGE(TIFF/JPEG/PNG/ZLIB) 模块（find_path/
        # find_library + 标准 FindZLIB），交叉链 FIND_ROOT_PATH_MODE=ONLY 覆盖命令行 → 直接预设
        # 各模块的 find 缓存变量（<pkg>/include + 实际 lib 文件）即绕过搜索。
        _wire = [
            # (conan 依赖, [INCLUDE 变量...], [LIBRARY 变量...], [lib 文件候选（优先 .so，回退 .a）])
            ("zlib",          ["ZLIB_INCLUDE_DIR"],           ["ZLIB_LIBRARY"],                   ["libz.so", "libz.a"]),
            ("libpng",        ["PNG_INCLUDE_DIR", "PNG_PNG_INCLUDE_DIR"], ["PNG_LIBRARY", "PNG_LIBRARY_RELEASE"], ["libpng.so", "libpng16.so", "libpng.a"]),
            ("libjpeg-turbo", ["JPEG_INCLUDE_DIR"],            ["JPEG_LIBRARY"],                   ["libjpeg.so", "libjpeg.a"]),
            ("libtiff",       ["TIFF_INCLUDE_DIR"],            ["TIFF_LIBRARY"],                   ["libtiff.so", "libtiff.a"]),
        ]
        _ldirs = []
        for _dep, _incvs, _libvs, _names in _wire:
            _pkg = self.dependencies[_dep].package_folder
            for _incv in _incvs:
                defs.append('-D{}="{}"'.format(_incv, os.path.join(_pkg, "include")))
            _lp = next((h for n in _names for h in glob.glob(os.path.join(_pkg, "lib", n))),
                       os.path.join(_pkg, "lib", _names[0]))
            for _lv in _libvs:
                defs.append('-D{}="{}"'.format(_lv, _lp))
            _ldirs.append(os.path.join(_pkg, "lib"))
        # 链接 libpano13.so 会牵出各依赖 .so 的传递 NEEDED（libtiff→libjpeg/libwebp/libzstd 等）
        # → 链接期加 -L + -rpath-link，运行期由 CI 的 LD_LIBRARY_PATH/conanrun 环境覆盖。
        # LDFLAGS 以 env 列表（追加到 conanrun 聚合环境）传入，仅对本次 cmake 进程生效，
        # 避免污染全局环境（R33 精神）。
        _ldflags = " ".join("-L{0} -Wl,-rpath-link,{0}".format(d) for d in _ldirs) + " " + os.environ.get("LDFLAGS", "")
        # OHOS SDK 的 lld 依赖 libxml2.so.16（位于 SDK native/llvm/lib，无 RUNPATH，纯靠
        # 加载器路径搜索）。CI worker 若不注入该目录，链接阶段报 "Error loading shared
        # library libxml2.so.16" → CMake 编译器自测失败（CMakeTestCCompiler）。显式把
        # SDK llvm/lib 加入 LD_LIBRARY_PATH 保证自包含（SKILL profile 同款修复）。
        _sdk_llvm = os.path.abspath(os.path.join(os.path.dirname(toolchain), "../../native/llvm/lib"))
        _ld_library_path = _sdk_llvm + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "") if os.path.isdir(_sdk_llvm) else os.environ.get("LD_LIBRARY_PATH", "")
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)),
                 env=["LDFLAGS=" + _ldflags, "LD_LIBRARY_PATH=" + _ld_library_path])
        self.run('cmake --build "{}" -- -j{}'.format(bdir, os.cpu_count() or 2),
                 env=["LDFLAGS=" + _ldflags, "LD_LIBRARY_PATH=" + _ld_library_path])

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # 鸿蒙 PC 对 dlopen 的 .so 校验代码签名：链接器自签在显式 dlopen 场景可能被拒
        # （Permission denied）。剥旧 .codesign + binary-sign-tool -selfSign 1 重签。
        # 与 libtiff 4.7.2 同法（archives/l/libtiff/4.7.2/conanfile.py）。
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = os.environ.get("OHOS_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("OHOS_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for so in sos:
            if os.path.islink(so):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["pano13"]
        self.cpp_info.includedirs = ["include/pano13"]
        # 上游同时安装 11 个命令行工具到 bin/（PTblender/PTmender/PTinfo 等），
        # 与软件级 commands.json（type=tool）口径一致，L0k/R38 判定为 CLI 工具包。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "libpano13")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
