#!/usr/bin/env python3
"""Conan recipe for gtkd 3.11.0 — D bindings and OO wrapper for GTK+ 3 (GNUmakefile).

上游（github.com/gtkd-developers/GtkD）是 GTK+ 3 的 **D 语言绑定**：`generated/` 下
已随源码附带 **预生成的绑定代码**（gtkd 906 个 .d，另有 sourceview/gstreamer/vte/peas/
gtkdgl 子包），本配方直接编译它们，**不需要**在构建期跑 gir-to-d 代码生成器。

【决定性的架构事实：运行期 dlopen，而非链接期依赖 GTK】
  `generated/gtkd/*/c/functions.d` 里每个符号都是
      Linker.link(gtk_window_new, "gtk_window_new", LIBRARY.GTK);
  由 `gtkd.Loader`（src/gtkd/Loader.d）在**运行期**用 dlopen/dlsym 解析，
  库名取自 `gtkd.paths`（Linux 分支：`libgtk-3.so.0` 等）。
  因此：
    · 构建期**不需要** GTK 头文件，也不需要 pkg-config —— GNUmakefile 里
      `SOFLAGS_*`（`pkg-config --libs-only-l gtk+-3.0 ...`）仅在
      `USE_RUNTIME_LINKER` 为空时才会用到；而它由
      `grep "Linker" generated/gtkd/atk/c/functions.d` 判定，实测有 278 处命中
      → SOFLAGS 分支被跳过 → **构建期零 GTK 依赖**（实测 make libs 在无 GTK
      环境下成功产出 5 个静态库）。
    · 但**运行期**必须能 dlopen 到那些 .so，故 requires gtk/librsvg 以保证消费方
      `conan install` 后 LD_LIBRARY_PATH 上就有它们。

【构建路径：GNUmakefile】
  上游只提供 GNUmakefile + dub.json（无 meson.build）。
    · dub.json —— 需要 dub，ohpcd 无该制品（与 gir-to-d 0.23.3 同一结论）
    · GNUmakefile —— 只需 DC（默认按 dmd→ldc→ldc2→gdc 探测）
  故走 GNUmakefile，与 gir-to-d 先例一致。

【OHOS 实测的两个构建事项】
  ① 编译器必须给**绝对路径**（唯一的致命项）：hnp CPython 的 subprocess 走
     posix_spawn、不搜 PATH（E405，cffi 适配同款），把裸名 `ldc2` 交给 make 会
     `No such file or directory`。本配方把 `DC` 设为 `<ldc>/bin/ldc2` 绝对路径
     （顺带满足 makefile 里 `findstring ldc,$(DC)` 的分支判定）。make 自身经
     /bin/sh 调 ar/ranlib，不受该限制（实测通过）。
  ② `make -j` 的 jobserver 警告（**非致命，不是失败原因**）：
        make: jobserver mkfifo: <tmp>/GMfifoNNN: Operation not permitted
     GNU make 的 jobserver 默认用 FIFO，OHOS 不允许创建；但 make 4.4.1 会自动
     回退到 pipe jobserver，构建照常完成 —— 实测**去掉** `--jobserver-style=pipe`
     直接 `make -j4 libs` 仍 **rc=0、5 个静态库全部产出**（警告照印）。
     本配方仍显式传该参数只为消噪音并兼容更老的 make，**不是成功必要条件**。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 子包及其静态库名（GNUmakefile: LIBNAME_<X> = lib<x>d-<MAJOR>.a，MAJOR=3）
SUBPACKAGES = ("gtkd", "sv", "gstreamer", "vte", "peas")

# GNUmakefile 内写死 GTKD_VERSION=3.10.0（本包版本为 3.11.0），但 MAJOR 仍为 3，
# 库名/安装目录都用 MAJOR → 不受影响；.pc 里的 Version 字段会显示 3.10.0，
# 本配方在 package() 用真实版本重写 .pc（见下）。
UPSTREAM_MAKEFILE_MAJOR = 3


class GtkdConan(ConanFile):
    name = "gtkd"
    version = "3.11.0"
    description = ("gtkd — D bindings and object-oriented wrapper for GTK+ 3 "
                   "(runtime-dlopen based)")
    # 上游 COPYING 为 LGPL-3.0-or-later "with additional exceptions"
    # （GtkD 的标准例外，允许静态链接专有程序）
    license = "LGPL-3.0-or-later"
    homepage = "https://gtkd.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 产物是静态绑定库 + D 导入源码（.d）；D 链接模型下由消费方静态链入。
    # 只做静态：GNUmakefile 的 shared-libs 需要 pkg-config 提供 gtk/librsvg 的
    # 链接参数，而 OHOS 上 pkg-config 对 conan 包并不天然可用；且 dlopen 型绑定
    # 无需自建 .so（与同仓 libffi 3.5.2 一样不声明 shared 选项）。
    package_type = "static-library"
    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 运行期 dlopen 目标（gtkd.paths 的 Linux 分支）。
        # gtk 传递带入 glib/gobject/gio/pango/cairo/gdk-pixbuf/atk/fribidi 等，
        # 实测 libgtk-3.so.0 / libgdk-3.so.0 / libgobject-2.0.so.0 / libgio-2.0.so.0
        # 均可 dlopen；librsvg 不在 gtk 传递闭包内（实测 librsvg-2.so.2 缺失），
        # 单独声明。
        #
        # cairo-gobject 版本冲突必须在此消解：gtk/3.24.43 钉 1.18.4.2，而
        # librsvg/2.62.3.1 钉 1.18.4.3，二者同时进图会让 conan 直接报
        #   ERROR: Version conflict: Conflict between cairo-gobject/1.18.4.3
        #          and cairo-gobject/1.18.4.2 in the graph.
        # 取较新的 1.18.4.3（ohpcd 已发布，且 librsvg 是更晚适配的版本）。
        self.requires("cairo-gobject/1.18.4.3", override=True)
        self.requires("gtk/3.24.43")
        self.requires("librsvg/2.62.3.1")

    def build_requirements(self):
        # D 工具链：ohpcd 已发布 ldc/1.42.0（os=OHOS, arch=armv8），含 ldc2、
        # druntime+Phobos（libdruntime-ldc.a / libphobos2-ldc.a / include/d/）。
        # 与 gir-to-d 0.23.3 同一先例。ldc recipe 的 package_info 已注入
        # DC/DMD/PATH/LD_LIBRARY_PATH（含其依赖 llvm/20.1.0 的 lib）。
        self.tool_requires("ldc/1.42.0")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32：平台判定必须用 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gtkd/3.11.0 only supports Linux/OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ---------------------------------------------------------------- helpers
    def _ldc(self):
        dep = self.dependencies.build["ldc"]
        pkg = dep.package_folder
        if not pkg:
            raise ConanException("ldc tool_requires provides no package_folder")
        dc = os.path.join(pkg, "bin", "ldc2")
        if not os.path.isfile(dc):
            raise ConanException(f"ldc2 not found in ldc package: {dc}")
        return pkg, dc

    def _phobos_include(self, ldc_pkg):
        """Phobos/druntime 的 D 源码导入路径（ldc2 默认搜索路径不含它）。

        实测：不给该 -I，编译即报 `unable to read module 'algorithm'`。
        """
        inc = os.path.join(ldc_pkg, "include", "d")
        if not os.path.isdir(os.path.join(inc, "std")):
            raise ConanException(f"ldc Phobos sources missing under {inc}")
        return inc

    # ------------------------------------------------------------------ build
    def build(self):
        ldc_pkg, dc = self._ldc()
        phobos = self._phobos_include(ldc_pkg)

        if not os.path.isfile(os.path.join(self.source_folder, "GNUmakefile")):
            raise ConanException(
                "upstream GNUmakefile not found — this recipe builds gtkd via the "
                "Makefile path (dub is unavailable on OHOS)")
        if not os.path.isdir(os.path.join(self.source_folder, "generated", "gtkd")):
            raise ConanException(
                "upstream generated/gtkd not found — 3.11.0 ships pre-generated "
                "bindings; regeneration would need gir-to-d + .gir files")

        jobs = build_jobs(self)
        # ① DC 用绝对路径（posix_spawn 不搜 PATH，E405）—— 唯一致命项
        # ② jobserver 警告是非致命的（GNU make 4.4.1 自动回退 pipe jobserver，
        #    实测去掉该开关 make -j4 仍 rc=0），这里传只为消噪音。
        jflag = f"--jobserver-style=pipe -j{jobs}" if jobs > 1 else ""
        cmd = (f'make -f GNUmakefile {jflag} libs '
               f'DC="{dc}" DCFLAGS="-O -I{phobos}"')
        self.output.info(f"building: {cmd}")
        self.run(cmd, cwd=self.source_folder)

        # 断言产物确实生成（不静默接受空结果）
        missing = [f"lib{n}-{UPSTREAM_MAKEFILE_MAJOR}.a"
                   for n in self._lib_names()
                   if not os.path.isfile(
                       os.path.join(self.source_folder,
                                    f"lib{n}-{UPSTREAM_MAKEFILE_MAJOR}.a"))]
        if missing:
            raise ConanException(f"gtkd build produced no {missing}")

    def _lib_names(self):
        # LIBNAME_GTKD=libgtkd-3.a, LIBNAME_GTKDSV=libgtkdsv-3.a,
        # LIBNAME_GSTREAMERD=libgstreamerd-3.a, LIBNAME_VTED=libvted-3.a,
        # LIBNAME_PEASD=libpeasd-3.a
        return ("gtkd", "gtkdsv", "gstreamerd", "vted", "peasd")

    # ---------------------------------------------------------------- package
    def package(self):
        major = UPSTREAM_MAKEFILE_MAJOR
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include", "d", f"gtkd-{major}")

        # 静态库
        for name in self._lib_names():
            copy(self, f"lib{name}-{major}.a", src=self.source_folder, dst=libdir)

        # D 导入源码：上游 install-headers-gtkd 用 SOURCES_GTKD =
        # generated/gtkd/*/*.d + generated/gtkd/*/c/*.d；子包各自并入同一
        # include/d/gtkd-3/ 目录（见 install-headers-gtkdsv 等规则）。
        for sub in SUBPACKAGES:
            src = os.path.join(self.source_folder, "generated",
                               "gtkd" if sub == "gtkd" else
                               {"sv": "sourceview"}.get(sub, sub))
            if not os.path.isdir(src):
                continue
            copy(self, "*.d", src=src, dst=incdir)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # pkg-config 描述（上游会由 makefile 生成，但其中 Library 路径写的是
        # 构建期 prefix、且 Version 取自写死的 GTKD_VERSION=3.10.0）。这里按本包
        # 真实版本与安装布局重写，使消费方 pkg-config 可用。
        pcdir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        with open(os.path.join(pcdir, f"gtkd-{major}.pc"), "w") as f:
            f.write(f"Name: GtkD\n")
            f.write("Description: A D binding and OO wrapper for GTK+.\n")
            f.write(f"Version: {self.version}\n")
            f.write(f"Libs: -L${{libdir}} -lgtkd-{major} -ldl\n")
            f.write(f"Cflags: -I${{includedir}}/d/gtkd-{major}/\n")
            f.write("Requires: gtk+-3.0, gdk-3.0, atk, pango, cairo, "
                    "cairo-gobject, pangocairo, librsvg-2.0, gio-2.0, "
                    "glib-2.0, gobject-2.0\n")

        # 载荷完整性
        if not os.path.isfile(os.path.join(libdir, f"libgtkd-{major}.a")):
            raise ConanException(f"libgtkd-{major}.a missing under {libdir}")
        if not os.path.isfile(os.path.join(incdir, "gtk", "Version.d")) and \
           not os.path.isfile(os.path.join(incdir, "gtkd", "Loader.d")):
            raise ConanException(f"D import sources missing under {incdir}")

    def package_info(self):
        major = UPSTREAM_MAKEFILE_MAJOR
        self.cpp_info.libs = [f"gtkd-{major}", f"gtkdsv-{major}",
                              f"gstreamerd-{major}", f"vted-{major}",
                              f"peasd-{major}"]
        self.cpp_info.includedirs = [os.path.join("include", "d", f"gtkd-{major}")]
        self.cpp_info.set_property("pkg_config_name", f"gtkd-{major}")
        if self.settings.os in ("Linux", "OHOS"):
            # gtkd.Loader 用 dlopen/dlsym（musl 把 dl 并入 libc，-ldl 仍可解析）
            self.cpp_info.system_libs = ["dl", "m", "pthread"]

        # 消费方编译 D 程序时需要 gtkd 的 D 导入路径（-I）。D 编译器/Phobos
        # 由 ldc 的 tool_requires 注入；此处只补 gtkd 自身，并以具名变量暴露，
        # 便于消费方 D 构建脚本引用（不覆盖通用的 DFLAGS）。
        inc = os.path.join(self.package_folder, "include", "d", f"gtkd-{major}")
        self.buildenv_info.define("GTKD_DFLAGS", f"-I{inc}")
