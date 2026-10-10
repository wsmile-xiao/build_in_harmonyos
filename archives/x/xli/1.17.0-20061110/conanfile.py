#!/usr/bin/env python3
"""Conan recipe for xli (X11 image display/manipulation utility).

Source: https://github.com/openSUSE/xli (upstream 1.17.0 snapshot, 2006-11-10)
Build system: Imake (Imakefile) —— OHOS 无 imake/xmkmf 工具链，
              使用上游自带的 Makefile.std 直接构建（README 给出的官方备选路径）。

平台适配要点（详见 notes.md）：
  1. Imake 构建不可用 → Makefile.std 直编（不需要 imake 生成的 Makefile）
  2. OHOS musl libc 未提供 BSD 遗留函数 rindex() → 编译期 -Drindex=strrchr
     （不用上游 -DSYSV 开关：该开关会引入 musl 同样缺失的 SysV F_FREESP）
  3. 上游 Makefile.std 的 install 目标只安装 xli，不安装 xlito → package() 补装
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, chdir
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class XliConan(ConanFile):
    name = "xli"
    version = "1.17.0-20061110"
    description = "xli - X11 image display/manipulation utility (xloadimage fork), with JPEG/PNG support"
    license = "MIT"
    homepage = "https://github.com/openSUSE/xli"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Xlib.h/libX11；XShm.h/libXext（xli 的 ddxli.h 直接包含 XShm.h）
        self.requires("libx11/6.4.0")
        self.requires("libxext/6.4.0")
        # 图像编解码：jpeg.c / png.c / zio.c 直接依赖
        self.requires("libjpeg/10")
        self.requires("libpng/1.6.58")
        self.requires("zlib/1.3.1.1")

    # R32: settings.os 判断必须兼容 OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: 编译器/基础标志由 Conan 工具链注入，不裸用 shell 环境变量
        tc = GnuToolchain(self)
        tc.generate()

    def _compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c") or str(self.settings.compiler)

    def _dependency_flags(self):
        """展开依赖的 -I/-L/-l（Makefile.std 不经 autotools，需显式传参）。"""
        includes, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            info = dep.cpp_info.aggregated_components()
            includes.extend(info.includedirs or [])
            libdirs.extend(info.libdirs or [])
            for name in info.libs or []:
                if name not in libs:
                    libs.append(name)
        inc_flags = " ".join(f"-I{p}" for p in dict.fromkeys(includes))
        ld_flags = " ".join(f"-L{p}" for p in dict.fromkeys(libdirs))
        lib_flags = " ".join(f"-l{n}" for n in libs)
        return inc_flags, ld_flags, lib_flags

    def build(self):
        apply_conandata_patches(self)
        inc_flags, ld_flags, lib_flags = self._dependency_flags()
        # 参数最少化：-O2 为上游 Makefile.std 默认，仅补平台必需项
        #   -DHAS_MEMCPY     : bcopy/bzero 走 memcpy/memset
        #   -Drindex=strrchr : OHOS musl 无 BSD 遗留 rindex()（index/bcopy/bzero 均存在）
        cflags = f"-O2 -DHAS_MEMCPY -Drindex=strrchr {inc_flags}"
        # xlito 为免显示命令行工具；xli 需要 X 显示（测试用例见 test_package）
        with chdir(self, self.source_folder):
            # R9: 固定 -j1（HMDFS/任务机限制）
            self.run(
                f"make -f Makefile.std -j1 all CC='{self._compiler()}' "
                f"CFLAGS='{cflags}' LIBS='{ld_flags} {lib_flags} -lm'"
            )

    def package(self):
        copy(self, "xli", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "xlito", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "*.man", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # CLI 工具包：仅暴露 bin/（commands.json 见软件级目录）
        self.cpp_info.bindirs = ["bin"]
