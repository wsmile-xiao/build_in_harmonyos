#!/usr/bin/env python3
"""Conan recipe — libgtop 2.41.3 (Autotools).

libgtop provides the GTop library that gives access to system information
(CPU, memory, processes, disks, network, etc.) on Unix-like systems.
Adapted to HarmonyOS PC (aarch64). See notes.md for platform adaptations.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibgtopConan(ConanFile):
    name = "libgtop"
    version = "2.41.3"
    description = "GTop library — system information access for GNOME (CPU, memory, processes, disks, network)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgtop"
    url = "https://gitlab.gnome.org/GNOME/libgtop"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libgtop is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES(GLIB, glib-2.0 >= 2.6.0 gobject-2.0 >= 2.26.0)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps emits glib-2.0.pc / gobject-2.0.pc for configure's
        # PKG_CHECK_MODULES. AutotoolsToolchain does not inject PKG_CONFIG_PATH
        # automatically, so point configure at the generators folder explicitly.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # OHOS libc 无 libintl；glib 的 gi18n-lib.h 会把 ngettext 宏映射为
        # g_libintl_ngettext 符号，禁用 NLS 后走 gettext fallback 不再引用。
        tc.configure_args.append("--disable-nls")
        _gens = self.generators_folder
        if _gens:
            tc.configure_args.append("PKG_CONFIG_PATH={}".format(_gens))
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # CI 环境无 texinfo（makeinfo 缺失），doc/ 的 libgtop2.info 生成依赖
        # MAKEINFO；注入 MAKEINFO=true 让 configure 不再回退 missing 脚本（缺
        # 失 makeinfo 时 missing 返回 127 → make Error 127）。
        tc.configure_args.append("MAKEINFO=true")
        # glib 包的 libintl.h 把 ngettext 宏映射为 g_libintl_ngettext，该符号由
        # glib 包内自带 libintl.so（proxy-libintl）提供，需显式链接 -lintl，
        # 否则 src/daemon 链接报 undefined symbol: g_libintl_ngettext。
        # 用 configure_args 传 LDFLAGS（写入 Makefile 链接行），tc.ldflags 在该
        # conan 版本不会序列化进 shell 导出（实测 env 中无 -lintl）。
        # LDFLAGS 带 -lintl 后 configure conftest 也链接 libintl.so.8，而该库在
        # glib 包私有 libdir，运行时不会被默认搜索路径找到（"cannot run C
        # compiled programs"）。加 -Wl,-rpath 让 conftest 与 daemon 运行时都能
        # 定位 libintl.so.8（buildenv LD_LIBRARY_PATH 注入在 aggregate env 未生效）。
        if "glib" in self.dependencies:
            _dep = self.dependencies["glib"]
            _pf = getattr(_dep, "package_folder", None) or ""
            for _l in _dep.cpp_info.libdirs:
                _libdir = _l if os.path.isabs(_l) else os.path.join(_pf, _l)
                if os.path.isdir(_libdir) and os.path.exists(os.path.join(_libdir, "libintl.so")):
                    tc.configure_args.append(
                        "LDFLAGS=-L{} -lintl -Wl,-rpath,{}".format(_libdir, _libdir))
                    break
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool *.la wrapper files.
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "**", "*.la"), recursive=True):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libgtop-2.0")
        # gtop-2.0 静态库的 read.c/write.c 经 glib 的 libintl.h 引用
        # g_libintl_ngettext，消费者必须链 glib 包自带的 libintl；把 intl 列入
        # libs 让生成 libgtop-2.0.pc 的 Libs 携带 -lintl（glib-2.0.pc 的 -L
        # 已指向其 libdir，可解析）。
        self.cpp_info.libs = ["gtop-2.0", "intl"]
        self.cpp_info.includedirs = ["include", "include/libgtop-2.0"]
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
