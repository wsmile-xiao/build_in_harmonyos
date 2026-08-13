#!/usr/bin/env python3
"""Conan recipe — bluez 5.79 (Linux Bluetooth protocol stack, tool package).

bluez 是工具/守护进程型软件包（bluetoothd + bluetoothctl/btmon 等命令行工具），
不是库包：make install 只安装可执行文件和配置文件（无 .so/.a/include 输出）。
OHOS 适配要点：
  - 无 systemd/udev：--disable-udev --disable-systemd
  - libical 未发布制品仓且 OBEX 为可选 profile：--disable-obex
  - ell 使用 bluez 内置版本（不启用 --enable-external-ell）
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
import os


class BluezConan(ConanFile):
    name = "bluez"
    version = "5.79"
    description = "Linux Bluetooth protocol stack (bluetoothd + bluetoothctl/btmon tools)"
    license = "GPL-2.0"
    homepage = "https://www.bluez.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 已发布制品仓 (W0 预检通过, 含 OHOS binary)
        self.requires("glib/2.84.0.1")
        self.requires("dbus/1.14.10")
        # client (bluetoothctl) 需要 readline 头文件, configure 硬性检查
        self.requires("readline/8.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS 无 systemd/udev; libical 未发布且 OBEX 为可选 profile
        tc.configure_args.append("--disable-udev")
        tc.configure_args.append("--disable-systemd")
        tc.configure_args.append("--disable-obex")
        # CI worker 可能缺 rst2man, 跳过 manpage 生成 (R1 参数最少化)
        tc.configure_args.append("--disable-manpages")
        tc.generate()
        # 环境 LDFLAGS 可能含系统路径 (如 -L/usr/local/lib) 且排在依赖之前,
        # 链接器会优先选中系统静态库 (libglib-2.0.a 缺 g_libintl_* 符号) 而非
        # conan 依赖包. 显式重定义 LDFLAGS: 依赖 libdir 前置, 系统路径保留在后
        dep_ldflags = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib):
                    dep_ldflags.append("-L" + lib)
        orig_ldflags = os.environ.get("LDFLAGS", "")
        env = Environment()
        # -lncursesw: bluez 硬编码 -lreadline 不带出 termcap 符号 (tputs/tgetent),
        # readline 静态库需 ncursesw 提供
        env.define("LDFLAGS", (" ".join(dep_ldflags) + " " + orig_ldflags + " -lncursesw").strip())
        # configure 的 AC_CHECK_HEADERS (readline/readline.h 等) 不通过 pkg-config,
        # 需将依赖 include 目录注入 CPPFLAGS (CI worker 无系统 readline 头文件)
        dep_cppflags = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                inc = os.path.join(dep.package_folder, "include")
                if os.path.isdir(inc):
                    dep_cppflags.append("-I" + inc)
        orig_cppflags = os.environ.get("CPPFLAGS", "")
        env.define("CPPFLAGS", (" ".join(dep_cppflags) + " " + orig_cppflags).strip())
        env.vars(self).save_script("ldflags_env")
        # 生成所有依赖 (含传递依赖) 的 .pc 文件到 generators 目录,
        # AutotoolsToolchain 已把该目录注入 PKG_CONFIG_PATH,
        # configure 的 pkg-config 检查 (glib-2.0/dbus-1/readline) 才能通过
        pkgconfig = PkgConfigDeps(self)
        pkgconfig.generate()
        # dbus 配方未声明 pkg_config_name=dbus-1, PkgConfigDeps 生成 dbus.pc,
        # 而 bluez configure 需要 dbus-1.pc 且查询 datadir/system_bus_services_dir/
        # session_bus_services_dir 变量, 补充生成 dbus-1.pc
        dbus_pc = os.path.join(self.generators_folder, "dbus.pc")
        if os.path.isfile(dbus_pc):
            with open(dbus_pc) as f:
                content = f.read()
            content = content.replace("Name: dbus", "Name: dbus-1")
            content += "\ndatadir=${prefix}/share"
            content += "\nsystem_bus_services_dir=${datadir}/dbus-1/system-services"
            content += "\nsession_bus_services_dir=${datadir}/dbus-1/services"
            save(self, os.path.join(self.generators_folder, "dbus-1.pc"), content)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 工具型包: 无可链接库, 只有 bindirs
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
