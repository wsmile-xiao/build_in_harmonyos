#!/usr/bin/env python3
"""Conan recipe — libhitaki 0.2.1 (Meson).

libhitaki: GObject 库，用于操作 IEEE 1394 (FireWire) 总线上的 ALSA audio/music
单元（DICE/Digi00x/EFW/MOTU/TASCAM/Fireface）的 HwDep 字符设备。
上游: https://github.com/alsa-project/libhitaki

HarmonyOS PC (aarch64) 适配要点：
- 构建系统为 Meson，依赖 gobject-2.0（>=2.44）。
- OHOS 目标侧无 gobject-introspection 工具链（g-ir-scanner 等不可执行，
  pygobject 亦无法加载 glib 共享库——HMDFS exec 限制），按仓库先例
  （glib/at-spi2-core 均禁 introspection）通过本仓补丁将 generate_gir
  选项化为 meson `introspection` 选项（默认开启），OHOS 构建关闭
  introspection（-D introspection=false），库本体、头文件与 pkg-config
  正常交付；GIR typelib 不生成（上游测试为 GI/Python 脚本，见 notes.md
  台账，需真实 IEEE1394 设备 + GI 运行环境）。
- gobject 来自已发布至 ohpcd 的 glib2 包；对消费者传递 headers
  （hitaki.h include 了 glib.h/glib-object.h），静态包用 transitive_headers。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.28"


class LibhitakiConan(ConanFile):
    name = "libhitaki"
    version = "0.2.1"
    description = ("Input/Output library to audio and music units on IEEE 1394 "
                   "bus (ALSA HwDep GObject API)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/alsa-project/libhitaki"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # meson dependency('gobject-2.0') 经 pkg-config 解析，PkgConfigDeps 生成 .pc
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 已确认发布到 ohpcd（conan download --only-recipe 验证）：
        # glib2/2.88.0（pulls pcre2/10.45, zlib/1.3.1）。transitive_headers:
        # hitaki.h 顶层 include 了 glib.h/glib-object.h，消费者编译必须拿到
        # glib 的 include 目录（静态包默认不传播传递依赖 headers）。
        self.requires("glib2/2.88.0", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 与 glib2/at-spi2-core 配方一致：CI worker 会导出 AR/AS/STRIP/NM/RANLIB
        # 为 llvm-* 裸名，meson archiver 探测用裸名在 PATH 找不到 → configure
        # 报 "Unknown linker(s)"。弹出这些变量并锁定真实工具（绝对路径）。
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]

        # 项目选项：OHOS 关闭 introspection（本仓补丁新增选项）与文档
        tc.project_options["doc"] = "false"
        tc.project_options["introspection"] = "false"
        tc.generate()

        # glib2 包只生成聚合的 glib-2.0.pc，meson 的 dependency('gobject-2.0')
        # 按单模块名查 → 找不到。按 at-spi2-core 先例补薄包装（Requires 指向
        # 聚合 glib-2.0.pc，静态 glib 的全部符号都从它继承）。
        self._write_compat_pc_files()

    def _write_compat_pc_files(self):
        glib = self.dependencies["glib2"].package_folder
        gens = self.generators_folder

        # glib-2.0.pc（PkgConfigDeps 已生成）：补 gnome.genmarshal/
        # mkenums_simple 所需的工具变量（libhitaki src/meson.build 会用
        # glib.get_pkgconfig_variable('glib_genmarshal') 等）。
        glib_pc = os.path.join(gens, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            with open(glib_pc, encoding="utf-8") as f:
                content = f.read()
            if "glib_genmarshal" not in content:
                content += (
                    "\nglib_genmarshal={gb}/bin/glib-genmarshal\n"
                    "glib_mkenums={gb}/bin/glib-mkenums\n"
                    "glib_compile_resources={gb}/bin/glib-compile-resources\n"
                    "glib_compile_schemas={gb}/bin/glib-compile-schemas\n"
                ).format(gb=glib)
            with open(glib_pc, "w", encoding="utf-8") as f:
                f.write(content)

        for name, desc in (
            ("gobject-2.0", "GLib Type, Object, Parameter and Signal Library"),
            ("gio-2.0", "glib I/O library"),
            ("gmodule-2.0", "Dynamic module loader for GLib"),
        ):
            pc = os.path.join(gens, f"{name}.pc")
            if os.path.isfile(pc):
                continue
            with open(pc, "w", encoding="utf-8") as f:
                f.write(
                    "prefix={glib}\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include\n"
                    "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                    "\n"
                    "Name: {name}\n"
                    "Description: {desc}\n"
                    "Version: 2.88.0\n"
                    "Requires: glib-2.0\n"
                    "Libs: -L\"${{libdir}}\"\n"
                    "Cflags: -I\"${{includedir}}\" -I\"${{includedir}}/glib-2.0\" "
                    "-I\"${{includedir1}}\"\n"
                    .format(name=name, desc=desc, glib=glib))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游测试为 Python GI 脚本（需 typelib + pygobject + 真实 firewire
        # 设备 + 可执行 mmap 的 glib 共享库），OHOS 侧运行条件全部缺失，
        # 不在 build() 里跑 meson test（详见 notes.md 台账与首错证据）。

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["hitaki"]
        # hitaki.h 需 glib2 的 include；库链接 gobject-2.0
        self.cpp_info.requires = ["glib2::glib2"]
        # meson 将头文件装入 $prefix/include/hitaki/（install_headers subdir），
        # 上游 pkg-config 亦返回 -I.../include/hitaki → #include <hitaki.h>
        self.cpp_info.includedirs = ["include/hitaki"]
        self.cpp_info.set_property("pkg_config_name", "hitaki")
        self.cpp_info.system_libs = ["m", "pthread", "dl", "rt"]