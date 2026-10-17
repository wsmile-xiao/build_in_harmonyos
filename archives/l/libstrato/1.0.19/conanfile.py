#!/usr/bin/env python3
"""Conan recipe — libstrato 1.0.19 (CMake / OHOS native HAL)

StratoHAL 是 ONScripter 系游戏引擎的 HAL 抽象层（图像/字形/音频/渲染后端）。
上游自带 `STRATO_TARGET_OPENHARMONY` 目标开关，但仓库
`cmake/toolchains/` 只提供 ios / linux / macos / mingw / openwatcom / unity
共 17 个工具链文件、**没有 openharmony**，且该目标的 target_link_libraries
直接点名 OHOS sysroot 原生库（libGLESv2 / libOpenSLES / librawfile.z.so），
源集里还有需要 C++ 的 ohmain.cpp / ohfile.cpp（enable_language(CXX)）
⇒ 本配方自建交叉工具链接设备 sysroot。

本包三个必须处理的环境事实（详见 notes.md）：
  1. 本机 `uname -s` = HarmonyOS，而 CMake 4.1.2 只带 420 个 Platform 模块、
     **不含 HarmonyOS/OHOS** ⇒ 必须显式 CMAKE_SYSTEM_NAME=Linux，
     否则 platform 检测落空。
  2. 上游 image.c / glyph.c / wave.c 按其自带 `lib/build-libs.sh` 安装出的
     **子目录头文件布局**写死 `#include <png/png.h>` / `<jpeg/jpeglib.h>`
     （该分支只认这一种），而 conan 包头文件是平铺的 ⇒ 在 build_folder 建
     私有 include 前缀补齐子目录（不改依赖包、不动上游源码）。
  3. OHOS 下 conan 的 CMakeToolchain 不写 CMAKE_SYSTEM_NAME/CMAKE_SYSROOT
     （generic_system 块为空），且本包依赖均走上游自带 Find 模块（MODULE 模式），
     交叉链下 find_* 结果须直接预置 ⇒ 用裸 cmake + 自建工具链，
     不走 conan_toolchain（仓库既有约定）。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout

# 上游 lib/build-libs.sh 的安装布局：这些依赖的头文件必须出现在同名子目录下
# （image.c: `#include <png/png.h>` / `#include <jpeg/jpeglib.h>`）。
_SUBDIR_HEADERS = {
    "libpng": "png",
    "libjpeg-turbo": "jpeg",
}


class LibstratoConan(ConanFile):
    name = "libstrato"
    version = "1.0.19"
    description = ("StratoHAL — hardware abstraction layer for the Strato runtime "
                   "(OpenHarmony/HarmonyOS PC native target)")
    license = "Zlib"
    homepage = "https://github.com/awemorris/StratoHAL"
    url = ""

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
        # 上游只支持 Unix-like 目标（OpenHarmony 分支链接 OHOS sysroot 原生库）。
        if str(self.settings.os) not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                f"{self.ref} 仅适配 OHOS（上游 STRATO_TARGET_OPENHARMONY 目标）"
            )

    def requirements(self):
        # 与上游 STRATO_ENABLE_DIST=ON（用系统库）的分支一一对应。
        # libpng 1.6.58.1+ 均 pin zlib/1.3.2，故此处显式对齐（旧 1.6.58 在制品仓
        # 无匹配 binary，见 notes.md）。
        self.requires("libpng/1.6.58.2")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libwebp/1.6.0")
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        self.requires("freetype/2.14.3")
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── OHOS 工具链发现 ──────────────────────────────────────────────

    @staticmethod
    def _find_tool(name):
        """按 环境变量 → PATH → 本机用户前缀 → 旧设备 hnp 前缀 的顺序找工具。"""
        env_key = "OHOS_" + name.upper().replace("-", "_")
        candidates = [
            os.environ.get(env_key),
            shutil.which(name),
            os.path.expanduser(f"~/usr/local/bin/{name}"),
            f"/data/service/hnp/bin/{name}",
        ]
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _require_tool(self, name):
        path = self._find_tool(name)
        if not path:
            raise ConanInvalidConfiguration(
                f"找不到 OHOS 工具 '{name}'；请设 {('OHOS_' + name.upper().replace('-', '_'))} "
                f"或将它放进 PATH"
            )
        return path

    @staticmethod
    def _sysroot_valid(root):
        """有效 sysroot 判据：usr/lib 树内存在 musl 启动对象 crti.o。

        CI worker 上 wrapper 落在 /data/service/hnp/bin，按 bindir/../sysroot
        推出的 /data/service/hnp/sysroot 是空壳（Scrt1.o/crti.o/-lc 全缺），
        显式写进 CMAKE_SYSROOT 会覆盖 wrapper 自带默认，try_compile 直接挂。
        """
        if not root or not os.path.isdir(root):
            return False
        return bool(glob.glob(os.path.join(root, "usr", "lib", "**", "crti.o"),
                              recursive=True))

    def _pick_sysroot(self, bindir):
        """sysroot 候选链：设备布局优先，CI 布局兜底；全无效返回 None。

        None ⇒ 调用方省略 CMAKE_SYSROOT，交回 wrapper 自带 sysroot
        （与其余过 CI 的包同路径），优于拿死路径覆盖默认。"""
        cands = [os.path.normpath(os.path.join(bindir, "..", "sysroot")),
                 os.path.expanduser("~/usr/local/sysroot")]
        cands += sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/"
                                  "native/sysroot"), reverse=True)
        for c in cands:
            if self._sysroot_valid(c):
                return c
        return None

    def _toolchain_file(self, dep_folders):
        """生成交叉工具链：OHOS clang 包装器（自带 -target/--sysroot/musl）
        + 显式系统名。PKG 一律预置 find 结果，故 lib/include 搜索放行 BOTH。"""
        cc = self._require_tool("aarch64-unknown-linux-ohos-clang")
        cxx = self._require_tool("aarch64-unknown-linux-ohos-clang++")
        bindir = os.path.dirname(cc)
        sysroot = self._pick_sysroot(bindir)
        ar = self._find_tool("llvm-ar")
        ranlib = self._find_tool("llvm-ranlib")
        strip = self._find_tool("llvm-strip")

        roots = ([sysroot] if sysroot else []) + [f for f in dep_folders if f]
        lines = [
            "# 由 libstrato conanfile.py 生成：OHOS 交叉工具链",
            # CMake 不带 Platform/HarmonyOS.cmake，而本机 uname -s=HarmonyOS，
            # 不显式指定系统名会落到未定义平台。
            "set(CMAKE_SYSTEM_NAME Linux)",
            "set(CMAKE_SYSTEM_PROCESSOR aarch64)",
            f'set(CMAKE_C_COMPILER "{cc}")',
            f'set(CMAKE_CXX_COMPILER "{cxx}")',
        ]
        for var, tool in (("CMAKE_AR", ar), ("CMAKE_RANLIB", ranlib), ("CMAKE_STRIP", strip)):
            if tool:
                lines.append(f'set({var} "{tool}")')
        if sysroot:
            lines.append(f'set(CMAKE_SYSROOT "{sysroot}")')
        lines += [
            "set(CMAKE_FIND_ROOT_PATH " + " ".join(f'"{r}"' for r in roots) + ")",
            "set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)",
            "set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)",
            "set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)",
            "set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)",
        ]
        path = os.path.join(self.build_folder, "ohos-aarch64-toolchain.cmake")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return path

    def _private_headers(self, dep_folders):
        """把 libpng / libjpeg-turbo 的头文件复制进 build_folder 私有前缀的
        `png/`、`jpeg/` 子目录——复刻上游 lib/build-libs.sh 的安装布局，
        使上游写死的 `#include <png/png.h>` / `<jpeg/jpeglib.h>` 成立。"""
        root = os.path.join(self.build_folder, "deps-prefix", "include")
        for dep_name, sub in _SUBDIR_HEADERS.items():
            src = os.path.join(dep_folders[dep_name], "include")
            if not os.path.isdir(src):
                raise ConanInvalidConfiguration(
                    f"依赖 {dep_name} 未提供 include 目录：{src}"
                )
            os.makedirs(os.path.join(root, sub), exist_ok=True)
            copy(self, "*.h", src=src, dst=os.path.join(root, sub))
        return root

    # ── 构建 ────────────────────────────────────────────────────────

    def build(self):
        # 本包无需补丁（上游自带 OHOS 目标与源码集），补丁管线显式保留。
        apply_conandata_patches(self)
        folders = {name: self.dependencies[name].package_folder
                   for name in ("libpng", "libjpeg-turbo", "libwebp", "libogg",
                                "libvorbis", "freetype", "zlib")}
        tc = self._toolchain_file(list(folders.values()))
        inc = self._private_headers(folders)

        cmake = self._find_tool("cmake") or "cmake"
        bdir = os.path.join(self.build_folder, "build")
        lib_type = "SHARED" if self.options.shared else "STATIC"

        # 上游 OHOS 分支只 link `m GLESv2 OpenSLES librawfile.z.so`，但源码实际
        # 还引用下列库，缺任一都会让产物带未解析符号，OHOS 加载器在重定位阶段
        # 直接报 `Error relocating libstrato.so.1: <sym>: symbol not found`：
        #   · libEGL.so          — ohmain.cpp 的 egl* 系列
        #   · libGLESv3.so       — glrender.c 用的是**核心 ES3 名** glGenVertexArrays /
        #                          glBindVertexArray / glDeleteVertexArrays；而 OHOS 的
        #                          libGLESv2.so 是单地址转发桩，只导出 OES 后缀名
        #                          （glGenVertexArraysOES…），核心名只在 libGLESv3.so 里
        #   · libhilog_ndk.z.so  — OH_LOG_Print
        #   · libace_ndk.z.so    — OH_NativeXComponent_*
        #   · libace_napi.z.so   — ohmain.cpp 的 napi_* 系列
        # 上游示例 App 正是在 App 层补这几个库（resources/projects/openharmony/
        # entry/src/main/cpp/CMakeLists.txt: suika3 libace_napi.z.so libace_ndk.z.so
        # librawfile.z.so libhilog_ndk.z.so EGL GLESv3 OpenSLES）；本包是库 ⇒
        # 必须由库自身声明。
        ohos_extra_libs = ("-lEGL -lGLESv3 -lhilog_ndk.z -lace_ndk.z -lace_napi.z")

        args = [
            cmake, "-S", self.source_folder, "-B", bdir,
            f"-DCMAKE_TOOLCHAIN_FILE={tc}",
            f"-DCMAKE_BUILD_TYPE={self.settings.build_type}",
            f"-DCMAKE_SHARED_LINKER_FLAGS={ohos_extra_libs}",
            f"-DSTRATO_ENABLE_{lib_type}=ON",
            "-DSTRATO_TARGET_OPENHARMONY=ON",
            # 用 conan 提供的依赖，不用仓库自带的 lib/archive 内嵌源码
            "-DSTRATO_ENABLE_DIST=ON",
            # 上游 install 块无条件 install(TARGETS stratopack)，而 stratopack
            # 只在 STRATO_ENABLE_PACK=ON 时存在 ⇒ INSTALL 打开会 configure 失败；
            # 且上游用 RUNTIME DESTINATION 装 .so（Linux 下 .so 是 LIBRARY 制品，
            # 根本装不出来）⇒ 关掉 install，由 package() 收产物。
            "-DSTRATO_ENABLE_INSTALL=OFF",
            "-DSTRATO_ENABLE_PACK=OFF",
            # 上游自带 Find 模块走 MODULE 模式，交叉链下直接预置 find 结果。
            f"-DPNG_INCLUDE_DIR={inc}",
            f"-DPNG_LIBRARY={folders['libpng']}/lib/libpng.so",
            f"-DJPEG_INCLUDE_DIR={inc}",
            f"-DJPEG_LIBRARY={folders['libjpeg-turbo']}/lib/libjpeg.so",
            f"-DWEBP_INCLUDE_DIR={folders['libwebp']}/include",
            f"-DWEBP_LIBRARY={folders['libwebp']}/lib/libwebp.so",
            f"-DOGG_INCLUDE_DIR={folders['libogg']}/include",
            f"-DOGG_LIBRARY={folders['libogg']}/lib/libogg.so",
            f"-DVORBIS_INCLUDE_DIR={folders['libvorbis']}/include",
            f"-DVORBIS_LIBRARY={folders['libvorbis']}/lib/libvorbis.so",
            f"-DVORBISFILE_LIBRARY={folders['libvorbis']}/lib/libvorbisfile.so",
            f"-DFREETYPE_INCLUDE_DIRS={folders['freetype']}/include/freetype2",
            f"-DFREETYPE_LIBRARY={folders['freetype']}/lib/libfreetype.so",
            f"-DZLIB_INCLUDE_DIR={folders['zlib']}/include",
            f"-DZLIB_LIBRARY={folders['zlib']}/lib/libz.a",
        ]
        self.run(" ".join(f'"{a}"' if " " in a else a for a in args),
                 cwd=self.build_folder)
        self.run(f'"{cmake}" --build "{bdir}" -j2', cwd=self.build_folder)

    # ── 打包 ────────────────────────────────────────────────────────

    def package(self):
        bdir = os.path.join(self.build_folder, "build")
        if self.options.shared:
            # 只收实体文件（.so.1.0.0），再按 SONAME 建符号链接，
            # 避免把三条软链复制成三份实体。
            copy(self, "libstrato.so*", src=bdir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "libstrato.a", src=bdir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "include", "strato"),
             dst=os.path.join(self.package_folder, "include", "strato"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_elf()

    def _sign_elf(self):
        """HarmonyOS 上共享库需自签名后才能被加载（SKILL §7）。"""
        if str(self.settings.os) != "OHOS":
            return
        signer = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not (signer and objcopy):
            self.output.warning("binary-sign-tool / llvm-objcopy 缺失，跳过 ELF 签名")
            return
        libdir = os.path.join(self.package_folder, "lib")
        for name in sorted(os.listdir(libdir)) if os.path.isdir(libdir) else []:
            path = os.path.join(libdir, name)
            if os.path.islink(path) or ".so" not in name:
                continue
            subprocess.run([objcopy, "--remove-section", ".codesign", path],
                           check=False, capture_output=True)
            signed = path + ".signed"
            r = subprocess.run(
                [signer, "sign", "-selfSign", "1", "-inFile", path,
                 "-outFile", signed, "-signAlg", "SHA256withECDSA"],
                capture_output=True, text=True)
            if r.returncode == 0 and os.path.isfile(signed):
                os.replace(signed, path)
                os.chmod(path, 0o755)
            else:
                self.output.warning(f"ELF 签名失败：{name} {(r.stderr or '')[:200]}")

    def package_info(self):
        self.cpp_info.libs = ["strato"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "StratoHAL")
        self.cpp_info.set_property("cmake_target_name", "StratoHAL::StratoHAL")
        self.cpp_info.set_property("pkg_config_name", "strato")
