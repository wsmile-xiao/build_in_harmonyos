#!/usr/bin/env python3
"""Conan recipe for XmHTML 1.1.10 (Motif HTML widget library).

Source: https://pkg.freebsd.org/ports-distfiles/XmHTML-1.1.10.tgz
        （FreeBSD ports 权威 distfile 镜像；上游 www.xmhtml.org 与 SourceForge
         release 文件均已不可达，URL 与 distinfo 一致）
Build system: 上游手写 Makefile（无 configure / Imake / CMake）。
        `make lib` 构建 lib/common + lib/Motif，产出 libXmHTML.a 与
        libXmHTML.so.1.1.10（SONAME libXmHTML.so.1.1）；上游无 install 目标，
        因此 package() 显式收集头文件/库并补 SONAME 软链。

平台适配要点（详见 notes.md）：
  1. Xft.h 属于 XmHTML 的**公共接口**（HAVE_XFT=1 时被 XmHTML.h 链入），
     它直接 #include <X11/extensions/Xrender.h> → libxrender/libxft/fontconfig/
     freetype 必须保持直接依赖且头文件对消费者可见（transitive_headers）。
  2. freetype 头位于 include/freetype2（ft2build.h），故构建期消费依赖声明的
     全部 includedirs，并补 freetype2 / fontconfig 子目录。
  3. 零源码补丁：上游特性宏已把 musl 缺口（rindex/bcopy/bzero/bcmp/
     sys_errlist）挡在编译路径之外（链接期 0 个 undefined reference）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, chdir, copy, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class XmhtmlConan(ConanFile):
    name = "xmhtml"
    version = "1.1.10"
    description = ("XmHTML - Motif widget library for displaying HTML documents "
                   "(rich-text widget with HTML 3.2 support)")
    license = "LGPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/xmhtml/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # libXmHTML 不是 OHOS 系统同名库（/lib、/lib64 无此基名），按仓库约定默认动态
    default_options = {"shared": True}
    def validate(self):
        # R32: settings.os 判断必须兼容 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # 本包零源码补丁（patches/ 为空表，conandata.yml patches 亦为空）；
        # 保留导出挂点：后续如需打补丁，放入 patches/ 并在 conandata.yml
        # patches 段登记即可。
        copy(self, "patches/*", self.recipe_folder, self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # 本包 conandata.yml 的 patches 为空（零源码改动）；apply 调用保留为
        # 后续如需打补丁的挂点，空表时为 no-op。
        apply_conandata_patches(self)

    def requirements(self):
        # 公共头链：XmHTML.h → <X11/Intrinsic.h>、<Xm/Xm.h>、<XmHTML/HTML.h>，
        # HAVE_XFT=1 时链入 <X11/Xft/Xft.h> → <X11/extensions/Xrender.h>。
        # 因此 X11/Motif/字体栈全部保留 transitive_headers + transitive_libs。
        # motif/libxt pin libx11/1.8.13，libxext/6.4.0.1 自带 libx11/6.4.0 pin：
        # 沿用既有化解方式 —— force 到 1.8.13 + 选 6.4.0.1 修订。
        self.requires(
            "libx11/1.8.13", force=True, transitive_headers=True, transitive_libs=True
        )
        self.requires("libxt/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True, transitive_libs=True)
        # Motif：库本体链接串 LIBS = -lXm -lXmu -lXt -lXext -lX11 -lSM -lICE
        self.requires("motif/2.3.8", transitive_headers=True, transitive_libs=True)
        self.requires("libxmu/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("libsm/1.2.6", transitive_libs=True)
        self.requires("libice/1.1.2", transitive_libs=True)
        # 图像/字体栈：HAVE_XPM / HAVE_XFT / HAVE_LIBJPEG / HAVE_LIBPNG 默认开启
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)
        self.requires("libxft/2.3.9", transitive_headers=True, transitive_libs=True)
        self.requires("libxrender/0.9.12", transitive_headers=True, transitive_libs=True)
        self.requires("freetype/2.14.3", transitive_headers=True, transitive_libs=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True, transitive_libs=True)
        self.requires("libpng/1.6.58.3", transitive_headers=True, transitive_libs=True)
        self.requires("libjpeg-turbo/3.2.0", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.2", transitive_libs=True)

    def generate(self):
        # R33: 编译器/基础标志由 Conan 工具链注入，不裸用 shell 环境变量
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        includes, libdirs, libs = self._dependency_flags()
        inc_flags = " ".join(f"-I{path}" for path in includes)
        ld_flags = " ".join(f"-L{path}" for path in libdirs)
        lib_flags = " ".join(f"-l{name}" for name in libs)
        # 参数最少化（R1）：上游 Makefile 自带 OS_DEFINES/IMAGEDEFINES/XFT_DEFINES，
        # 交叉编译只需补依赖头目录与链接串（EXTRA_INCLUDES/EXTRA_CFLAGS/LOADLIBES
        # 是上游 Makefile 预留的覆盖点）。
        extra_cflags = f"-O2 -fPIC -I{self.source_folder} {inc_flags}"
        with chdir(self, self.source_folder):
            # R9: 固定 -j1（HMDFS/任务机限制）。上游无 install 目标，产物留在 lib/。
            self.run(
                "make -j1 lib "
                f"CC='{self._compiler()}' "
                f"EXTRA_CFLAGS='{extra_cflags}' "
                f"EXTRA_INCLUDES='{inc_flags}' "
                f"LOADLIBES='{ld_flags} {lib_flags}'"
            )

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # 头文件保持上游布局：include/XmHTML/*.h + include/common/*.h
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        if self.options.shared:
            copy(
                self,
                "libXmHTML.so.1.1.10",
                src=os.path.join(self.source_folder, "lib"),
                dst=os.path.join(self.package_folder, "lib"),
            )
            # 上游只产出带完整版本号的文件（无 libXmHTML.so 短名），补 SONAME 软链；
            # HMDFS 不能 ln -sf 覆盖，先删后建（R1）。
            for alias in ("libXmHTML.so.1.1", "libXmHTML.so"):
                link = os.path.join(self.package_folder, "lib", alias)
                if os.path.lexists(link):
                    os.remove(link)
                os.symlink("libXmHTML.so.1.1.10", link)
        else:
            copy(
                self,
                "libXmHTML.a",
                src=os.path.join(self.source_folder, "lib"),
                dst=os.path.join(self.package_folder, "lib"),
            )

    def package_info(self):
        self.cpp_info.libs = ["XmHTML"]
        # 传递传播由 requirements() 的 transitive_headers/transitive_libs 承担：
        # cpp_info.requires 只接受 "包::组件" 形式（根级裸包名会被当作本包内部
        # 组件而报错），而各依赖组件命名不一，故不在此重复声明。
        self.cpp_info.set_property("cmake_file_name", "XmHTML")
        self.cpp_info.set_property("cmake_target_name", "XmHTML::XmHTML")

    # ------------------------------------------------------------------
    # 手写 Makefile 辅助（镜像 xmcd 3.3.2 的已验证实现）
    # ------------------------------------------------------------------

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        # 目标机为 aarch64，OHOS SDK clang 为平台原生工具链（默认目标即
        # aarch64-linux-ohos），故与 xmcd/xli 一致只传编译器本体。
        return compilers.get("c") or str(self.settings.compiler)

    def _dependency_flags(self):
        """展开依赖的 -I/-L/-l（手写 Makefile 不经 autotools，需显式传参）。"""
        includes, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            # 只取 host 上下文且已安装的包：build/test 侧依赖（graph 中的
            # "Skipped binaries"，如 glib 等测试依赖）没有 package_folder。
            if getattr(dep, "context", "host") == "build":
                continue
            if not dep.package_folder:
                continue
            info = dep.cpp_info.aggregated_components()
            includes.extend(info.includedirs or [])
            libdirs.extend(info.libdirs or [])
            for name in info.libs or []:
                if name not in libs:
                    libs.append(name)
            # freetype 头在 include/freetype2、fontconfig 头在 include/fontconfig：
            # 依赖未声明时补上，保证 ft2build.h / fontconfig.h 可解析。
            for subdir in ("include/freetype2", "include/fontconfig"):
                candidate = os.path.join(dep.package_folder, subdir)
                if os.path.isdir(candidate):
                    includes.append(candidate)
        return list(dict.fromkeys(includes)), list(dict.fromkeys(libdirs)), libs
