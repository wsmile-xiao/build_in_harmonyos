#!/usr/bin/env python3
"""Conan recipe for alex4 1.1 — Alex the Allegator 4 (platform game, C/Allegro 4).

alex4 是 2003 年 Free Lunch Design 的经典平台游戏（C 语言）。上游源码包
（alex4src_data.zip）无 Makefile，readme 说明"just compile all the source files"。

依赖：
- allegro4.4（已合入 build_in_harmonyos，ohpcd remote 有 4.4.3.1 制品，conan 依赖）
- DUMB（aldumb.h + libaldmb/libdumb，音频库；项目未适配 → 配方内自包含构建
  dumb-0.9.3，参照 aegean 自包含 genometools 先例）

OHOS 适配要点：
- CI worker 网络受限（SourceForge 下载不稳定）→ 源码 zip + dumb 源码 tar 随
  export_sources 提供（参照 lv 先例），source() 本地解压。
- 必须应用 extras/alex4_unix.diff.gz（官方 Unix 补丁）：原代码音频驱动选择
  case 2/3 用 DIGI_DIRECTX/DIGI_DIRECTAMX（仅 Windows 定义），Unix 上编译失败；
  补丁改为 #ifdef ALLEGRO_WINDOWS / ALLEGRO_UNIX（DIGI_OSS/DIGI_ALSA 可选）。
- 编译：clang 编译全部 src/*.c（-I src -I data -I <allegro> -I <dumb>），
  链接 libaldmb.a + libdumb.a + liballeg。
- 上游无测试套件（游戏，readme 无 test 说明）→ 上游测试 0；消费测试验证
  二进制存在 + ELF 类型 + 依赖库可解析（游戏需显示驱动，headless 无法实跑）。
"""
import os
import shutil
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# 编译工具（OHOS NDK 固定路径；AR 用于静态库打包）
_CC = "/data/service/hnp/bin/clang"
_AR = "/data/service/hnp/bin/llvm-ar"


class Alex4Conan(ConanFile):
    name = "alex4"
    version = "1.1"
    description = "Alex the Allegator 4 — classic retro platform game (C/Allegro 4)"
    license = "GPL-2.0-or-later"
    homepage = "https://allegator.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # allegro4.4 已合入 build_in_harmonyos（ohpcd remote 有 4.4.3.1 制品）
        self.requires("allegro4.4/4.4.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"alex4 {self.version} only supports Linux/OHOS, got os={self.settings.os}")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # alex4 官方 SourceForge 实测可达（HTTP 200）→ 源码走 conandata sources.url
        # 官方 get() 下载（R39），不再 bundled zip（gitcode PR diff 无法应用新增
        # 二进制 alex4src_data.zip → checkout-pr 失败）。
        # dumb 同为官方 SourceForge get() 下载（conandata dumb 段，sha256 已核对），
        # 不再 bundled dumb-src/ 文本目录（归档只留配方/清单/补丁/测试）。
        # Allegro 定点数学兼容实现（OHOS 版 allegro4.4 无 fsin/fcos/fmul 符号）
        copy(self, "compat_fixed.c", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def source(self):
        # 1) alex4 源码：官方 SourceForge get() 下载解压（strip_root 剥 alex4src/ 顶层）
        get(self, **self.conan_data["sources"], strip_root=True)
        # 2) dumb 源码：官方 SourceForge get() 下载解压到 dumb/ 子目录
        #    （conandata dumb 段 URL + sha256 实测核对，strip_root 剥 dumb-0.9.3/ 顶层）
        import tarfile
        dumb_tar = os.path.join(self.source_folder, "dumb-0.9.3.tar.gz")
        get(self, **self.conan_data["dumb"])
        dumb_dst = os.path.join(self.source_folder, "dumb")
        os.makedirs(dumb_dst, exist_ok=True)
        inner = os.path.join(self.source_folder, "dumb-0.9.3")
        if os.path.isdir(inner):
            for _f in os.listdir(inner):
                shutil.move(os.path.join(inner, _f), dumb_dst)
            os.rmdir(inner)

    def _build_dumb(self, cc, allegro_inc):
        """自包含构建 dumb-0.9.3：libdumb.a（core+helpers+it）+ libaldmb.a（allegro 接口）。"""
        dumb_src = os.path.join(self.source_folder, "dumb")
        inc = os.path.join(dumb_src, "include")
        obj = os.path.join(self.build_folder, "dumb-obj")
        os.makedirs(obj, exist_ok=True)
        cflags = f"-O2 -I{inc}"
        # libdumb.a: src/core + src/helpers + src/it
        core_srcs = []
        for sub in ("core", "helpers", "it"):
            for f in sorted(os.listdir(os.path.join(dumb_src, "src", sub))):
                if f.endswith(".c"):
                    core_srcs.append(os.path.join(dumb_src, "src", sub, f))
        objs = []
        for i, s in enumerate(core_srcs):
            o = os.path.join(obj, f"core{i}.o")
            self.run(f"{cc} {cflags} -c {s} -o {o}")
            objs.append(o)
        core_archive = os.path.join(self.build_folder, "libdumb.a")
        self.run(f"{_AR} rcs {core_archive} " + " ".join(objs))
        # libaldmb.a: src/allegro（需要 allegro.h）
        aldmb_srcs = []
        for f in sorted(os.listdir(os.path.join(dumb_src, "src", "allegro"))):
            if f.endswith(".c"):
                aldmb_srcs.append(os.path.join(dumb_src, "src", "allegro", f))
        objs2 = []
        for i, s in enumerate(aldmb_srcs):
            o = os.path.join(obj, f"al{i}.o")
            self.run(f"{cc} {cflags} -I{allegro_inc} -c {s} -o {o}")
            objs2.append(o)
        aldmb_archive = os.path.join(self.build_folder, "libaldmb.a")
        self.run(f"llvm-ar rcs {aldmb_archive} " + " ".join(objs2))
        return os.path.join(self.build_folder, "libdumb.a"), \
            os.path.join(self.build_folder, "libaldmb.a"), inc

    def build(self):
        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # allegro4.4 依赖的 include 路径
        deps = self.dependencies
        allegro = deps["allegro4.4"]
        allegro_inc = os.path.join(allegro.package_folder, "include")
        # 1) 应用官方 Unix 补丁（extras/alex4_unix.diff.gz）：
        #    音频驱动 case 2/3 原为 DIGI_DIRECTX（仅 Windows），Unix 编译失败。
        #    注意：上游源码为 DOS 换行（FreeBSD port USES=dos2unix），先转 LF 再 patch。
        diff_gz = os.path.join(self.source_folder, "extras", "alex4_unix.diff.gz")
        if os.path.exists(diff_gz):
            import gzip
            with gzip.open(diff_gz, "rt", encoding="latin-1") as f:
                diff_text = f.read()
            diff_file = os.path.join(self.build_folder, "alex4_unix.diff")
            with open(diff_file, "w", encoding="latin-1") as f:
                f.write(diff_text)
            # DOS CRLF → LF（补丁上下文按 LF 写；CR 会破坏行尾匹配）
            self.run(f"cd {self.source_folder} && "
                     f"find src -type f \\( -name '*.c' -o -name '*.h' \\) -exec sed -i 's/\\r$//' {{}} +")
            self.run(f"cd {self.source_folder} && patch -p0 < {diff_file}")
        # 2) 自包含构建 dumb
        dumb_archive, aldmb_archive, dumb_inc = self._build_dumb(cc, allegro_inc)
        # 3) 编译 alex4：全部 src/*.c
        src_dir = os.path.join(self.source_folder, "src")
        data_dir = os.path.join(self.source_folder, "data")
        obj_dir = os.path.join(self.build_folder, "alex4-obj")
        os.makedirs(obj_dir, exist_ok=True)
        srcs = sorted(f for f in os.listdir(src_dir) if f.endswith(".c"))
        objs = []
        for f in srcs:
            o = os.path.join(obj_dir, f.replace(".c", ".o"))
            # -fcommon：2003 年旧代码多个 .c 各自定义全局变量（fps/lps/game_count 等），
            # clang 默认 -fno-common 报 duplicate symbol；-fcommon 合并 common 符号
            # （FreeBSD port 用旧 gcc 默认即 common 合并行为）
            self.run(f"{cc} -fcommon -O2 -I{src_dir} -I{data_dir} -I{allegro_inc} -I{dumb_inc} "
                     f"-c {os.path.join(src_dir, f)} -o {o}")
            objs.append(o)
        out_bin = os.path.join(self.build_folder, "alex4")
        # 编译 Allegro 定点数学兼容实现（OHOS 版 allegro4.4 无 fsin/fcos/fmul 符号，
        # alcompat.h 无宏映射；compat_fixed.c 按 Allegro 4 语义补全，链接 -lm）
        compat_o = os.path.join(obj_dir, "compat_fixed.o")
        self.run(f"{cc} -O2 -c {os.path.join(self.export_sources_folder, 'compat_fixed.c')} -o {compat_o}")
        objs.append(compat_o)
        self.run(f"{cc} -o {out_bin} " + " ".join(objs) +
                 f" {aldmb_archive} {dumb_archive} -L{allegro.package_folder}/lib -lalleg -lm")

    def package(self):
        copy(self, "alex4", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # 数据文件（data/*.dat 运行时需要）
        copy(self, "*.dat", src=os.path.join(self.source_folder, "data"),
             dst=os.path.join(self.package_folder, "share", "alex4", "data"))
        copy(self, "alex4.ini", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "alex4"))
        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
