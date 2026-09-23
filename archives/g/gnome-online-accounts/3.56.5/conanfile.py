#!/usr/bin/env python3
"""Conan recipe — gnome-online-accounts 3.56.5（GNOME 在线账户核心库）.

gnome-online-accounts（GOA）是 GNOME 系统服务，为在线账户（Google、
Nextcloud、Microsoft 等）提供单点登录。本配方构建核心库 libgoa（客户端 API），
goabackend 及各 provider 禁用（OHOS 无桌面环境）。

构建系统：Meson
依赖：glib（gio-2.0、gio-unix-2.0、glib-2.0）
测试：上游无自动化测试（meson.build 无 test() 调用）
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class GnomeOnlineAccountsConan(ConanFile):
    name = "gnome-online-accounts"
    version = "3.56.5"
    description = "GNOME Online Accounts — core client library (libgoa)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gnome-online-accounts"
    url = "https://gitlab.gnome.org/GNOME/gnome-online-accounts"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        self.requires("glib/2.88.0")
        self.requires("dbus/1.14.10")
        # registry zlib/1.3.1 静态库非 PIC，链进 libgoa-1.0.so 报
        # R_AARCH64 relocation（apk-tools 先例）；override 到鸿蒙 fPIC 定制版
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        # 禁用 goabackend（依赖 libsecret/rest/libadwaita/gcr4 等不可用包）
        # 及所有 provider（Google/Exchange/ownCloud/WebDAV/IMAP/Kerberos）
        tc.project_options["goabackend"] = False
        tc.project_options["google"] = False
        tc.project_options["exchange"] = False
        tc.project_options["fedora"] = False
        tc.project_options["imap_smtp"] = False
        tc.project_options["kerberos"] = False
        tc.project_options["owncloud"] = False
        tc.project_options["webdav"] = False
        tc.project_options["ms_graph"] = False
        # 禁用文档/内省/man/vapi
        tc.project_options["introspection"] = False
        tc.project_options["documentation"] = False
        tc.project_options["man"] = False
        tc.project_options["vapi"] = False
        tc.generate()
        PkgConfigDeps(self).generate()
        # glib/dbus 包的 .pc 文件用 prefix="/" 导致路径变为 //bin/...，
        # meson 找不到工具。复制并修正 prefix 为包实际路径
        pc_out_dir = os.path.join(self.generators_folder)
        for dep_name in ("glib", "dbus"):
            dep_pkg = self.dependencies[dep_name].package_folder
            dep_pc_dir = os.path.join(dep_pkg, "lib", "pkgconfig")
            if not os.path.isdir(dep_pc_dir):
                continue
            for pc_name in os.listdir(dep_pc_dir):
                if not pc_name.endswith(".pc"):
                    continue
                src_path = os.path.join(dep_pc_dir, pc_name)
                dst_path = os.path.join(pc_out_dir, pc_name)
                # 始终覆盖（glib 包 .pc 有 gdbus_codegen 等变量，
                # PkgConfigDeps 生成的版本缺少这些变量）
                with open(src_path) as src:
                    content = src.read()
                content = content.replace("prefix=/", "prefix=%s" % dep_pkg)
                with open(dst_path, "w") as f:
                    f.write(content)
        # dbus 包不含 dbus-1.pc，需手动生成以满足 meson 的 dbus-1 依赖检查
        dbus_pkg = self.dependencies["dbus"].package_folder
        pc_dir = os.path.join(self.generators_folder)
        pc_file = os.path.join(pc_dir, "dbus-1.pc")
        if not os.path.exists(pc_file):
            with open(pc_file, "w") as f:
                f.write("prefix=%s\n" % dbus_pkg)
                f.write("exec_prefix=${prefix}\n")
                f.write("libdir=${prefix}/lib\n")
                f.write("includedir=${prefix}/include/dbus-1.0\n")
                f.write("datadir=${prefix}/share\n")
                f.write("session_bus_services_dir=${datadir}/dbus-1/services\n")
                f.write("Name: dbus-1\n")
                f.write("Description: D-Bus library\n")
                f.write("Version: 1.14.10\n")
                f.write("Libs: -L${libdir} -ldbus-1\n")
                f.write("Cflags: -I${includedir}\n")
        # 修正 native file 中的编译器路径（MesonToolchain 用裸名 clang/clang++，
        # CI 上 /data/service/hnp/bin/ 不在默认 PATH，需写绝对路径）
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "")
        # 若 compiler_executables 未声明 ar，从 cc 同目录推导
        if not ar and "/" in cc:
            cc_dir = os.path.dirname(cc)
            for candidate in ("llvm-ar", "ar"):
                p = os.path.join(cc_dir, candidate)
                if os.path.isfile(p):
                    ar = p
                    break
        native_ini = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.isfile(native_ini) and "/" in cc:
            old = open(native_ini).read()
            # MesonToolchain 可能用单引号或双引号
            new = old.replace("c = 'clang'", "c = '%s'" % cc)
            new = new.replace('c = "clang"', 'c = "%s"' % cc)
            new = new.replace("cpp = 'clang++'", "cpp = '%s'" % cxx)
            new = new.replace('cpp = "clang++"', 'cpp = "%s"' % cxx)
            if ar:
                # native ini 可能无 ar 行 → 在 [binaries] 段末尾追加
                if "ar = " not in new:
                    new = new.replace("cpp = 'clang++'", "cpp = '%s'\nar = '%s'" % (cxx, ar))
                    new = new.replace('cpp = "clang++"', 'cpp = "%s"\nar = "%s"' % (cxx, ar))
                else:
                    new = new.replace("ar = 'llvm-ar'", "ar = '%s'" % ar)
                    new = new.replace("ar = 'ar'", "ar = '%s'" % ar)
            if new != old:
                open(native_ini, "w").write(new)
                self.output.info(f"Patched compiler in native ini: CC={cc}")

    def build(self):
        import subprocess
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "")
        if not ar and "/" in cc:
            cc_dir = os.path.dirname(cc)
            for c in ("llvm-ar", "ar"):
                p = os.path.join(cc_dir, c)
                if os.path.isfile(p):
                    ar = p
                    break
        # 生成正确的 native file（直接写绝对路径，避免裸名 clang 找不到）
        native_file = os.path.join(self.build_folder, "conan_meson_native.ini")
        with open(native_file, "w") as f:
            f.write("[binaries]\n")
            f.write(f"c = '{cc}'\n")
            f.write(f"cpp = '{cxx}'\n")
            if ar:
                f.write(f"ar = '{ar}'\n")
        env = dict(os.environ)
        env["CC"] = cc
        env["CXX"] = cxx
        if ar:
            env["AR"] = ar
        pc_path = os.path.join(self.generators_folder)
        dbus_pc_path = os.path.join(self.dependencies["dbus"].package_folder,
                                    "lib", "pkgconfig")
        glib_pc_path = os.path.join(self.dependencies["glib"].package_folder,
                                    "lib", "pkgconfig")
        env["PKG_CONFIG_PATH"] = f"{pc_path}:{dbus_pc_path}:{glib_pc_path}"
        # 传递 pkg-config 路径给 meson
        meson_pkg_path = f"{pc_path}:{dbus_pc_path}:{glib_pc_path}"
        build_dir = os.path.join(self.build_folder, "build-release")
        # meson setup
        cmd_setup = (
            f"meson setup --native-file {native_file} "
            f"--pkg-config-path {meson_pkg_path} "
            f"-Dintrospection=false -Ddocumentation=false -Dman=false -Dvapi=false "
            f"-Dgoabackend=false -Dgoogle=false -Dexchange=false -Dfedora=false "
            f"-Dimap_smtp=false -Dkerberos=false -Downcloud=false -Dwebdav=false -Dms_graph=false "
            f"{build_dir} {self.source_folder} --prefix=/"
        )
        r = subprocess.run(cmd_setup, shell=True, cwd=self.source_folder,
                           env=env, capture_output=True, text=True, timeout=300)
        print(r.stdout[-3000:])
        if r.returncode != 0:
            print(r.stderr[-3000:])
            raise Exception(f"meson setup failed: rc={r.returncode}")
        # meson compile
        r2 = subprocess.run(
            f"meson compile -C {build_dir}",
            shell=True, cwd=self.source_folder,
            env=env, capture_output=True, text=True, timeout=600)
        print(r2.stdout[-3000:])
        if r2.returncode != 0:
            print(r2.stderr[-3000:])
            raise Exception(f"meson compile failed: rc={r2.returncode}")

    def package(self):
        # build() 用嵌套目录 build-release/build-release（basic_layout 的
        # build_folder 是 .../build-release），Meson 助手默认取 self.build_folder
        # 会找不到 meson.build → 直接对实际构建目录执行 meson install
        # 注意：不覆盖 PATH（meson 在 user local bin，须继承 os.environ）
        import subprocess
        build_dir = os.path.join(self.build_folder, "build-release")
        env = dict(os.environ)
        r = subprocess.run(
            f"meson install -C {build_dir} --destdir {self.package_folder}",
            shell=True, cwd=self.source_folder, env=env,
            capture_output=True, text=True, timeout=300)
        print(r.stdout[-3000:])
        if r.returncode != 0:
            print(r.stderr[-3000:])
            raise Exception(f"meson install failed: rc={r.returncode}")

    def package_info(self):
        # 库名 libgoa-1.0（goa_api_name = 'goa-1.0'）
        self.cpp_info.libs = ["goa-1.0"]
        # 头文件安装到 include/goa-1.0/（goa_pkgincludedir）
        self.cpp_info.includedirs = ["include/goa-1.0"]
        self.cpp_info.requires = ["glib::glib", "dbus::dbus"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]
        self.cpp_info.set_property("pkg_config_name", "goa-1.0")
