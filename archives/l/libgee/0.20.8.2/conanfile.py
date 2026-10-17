#!/usr/bin/env python3
"""Conan recipe for libgee 0.20.8.2 — GObject collection library (Autotools).

Build system: Autotools (configure + make)。
核心依赖：glib（PKG_CHECK_MODULES 检查 glib-2.0/gobject-2.0/gio-2.0 >= 2.36）。
官方 tarball 自带预生成的 .c 文件与 vala stamp（gee/libgee_0_8_la_vala.stamp、
tests/tests_vala.stamp），VALA_CHECK 检测到 checkfile 存在 → enable_vala=no，
构建不需要 valac；GOBJECT_INTROSPECTION_CHECK 默认 auto，OHOS 无 GI 时自动降级。
config.guess/config.sub 需加 HarmonyOS → aarch64-unknown-linux-ohos 支持（补丁 0001/0002）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibgeeConan(ConanFile):
    name = "libgee"
    version = "0.20.8.2"
    description = "GObject-based interfaces and classes for commonly used data structures"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Projects/Libgee"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 裸格式引用（ohpcd 制品仓无 user/channel）。
        # transitive_headers/libs=True：gee-0.8.pc Requires glib-2.0/gobject-2.0，
        # 消费方（如 granite）与 test_package 需要 glib 的头文件/库路径。
        self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 遍历全部依赖（含 glib 的传递依赖 pcre2 等）：glib-2.0.pc 的
        # Requires 链需要 libpcre2-8.pc 等，须把所有依赖的 pkgconfig
        # 目录与 include/lib 路径注入，configure 的 PKG_CHECK_MODULES 才能通过。
        for dep in self.dependencies.values():
            for inc in dep.cpp_info.includedirs:
                tc.extra_cflags.append(f"-I{inc}")
            for libdir in dep.cpp_info.libdirs:
                tc.extra_ldflags.append(f"-L{libdir}")
                tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")
        env = tc.environment()
        for dep in self.dependencies.values():
            # ⭐ E-双副本修复（R60/libgsf 同款先例）：本机基础环境 LDFLAGS 含
            # -L/storage/Users/currentUser/usr/local/lib，AutotoolsToolchain 把
            # extra_ldflags 追加在其后 → 链接期 ld 先命中系统 /usr/local/lib 的
            # 共享 libglib-2.0.so，导致 libgee-0.8.so NEEDED 系统 glib（glib 包为
            # R26 静态-only，无 .so）→ 运行时 libgee 加载系统 glib、test_package
            # 内嵌 conan 静态 glib，两份 GObject 类型系统（quark/type-id 跨副本
            # 失效）→ "g_type_register_static: assertion 'static_quark_type_flags'"
            # 崩溃。把依赖包 lib 目录前置进 LDFLAGS，让链接期命中包内静态
            # libglib-2.0.a 等，libgee-0.8.so 内嵌 conan glib（与 test_package
            # 同一构建），运行期符号插桩收敛为单副本。
            for libdir in dep.cpp_info.libdirs:
                env.prepend("LDFLAGS", f"-L{libdir}")
            # configure 用 PKG_CHECK_MODULES 检查 glib-2.0/gobject-2.0/gio-2.0
            pkg_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkg_dir):
                env.append_path("PKG_CONFIG_PATH", pkg_dir)
            # make check 需要 gtester（glib 包 bin）
            bin_dir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.append_path("PATH", bin_dir)
            # gtester/tests 运行需要 glib 动态库
            for libdir in dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
        tc.generate(env=env)

        # glib-2.0.pc Requires: libpcre2-8 >= 10.32，但 pcre2 包未安装
        # .pc 文件。同 glib 配方：用 PkgConfigDeps 生成 pcre2.pc 后复制为
        # libpcre2-8.pc（Name 替换），并加入 PKG_CONFIG_PATH。
        PkgConfigDeps(self).generate()
        pcre2_pc = os.path.join(self.generators_folder, "pcre2.pc")
        libpcre2_pc = os.path.join(self.generators_folder, "libpcre2-8.pc")
        if os.path.exists(pcre2_pc) and not os.path.exists(libpcre2_pc):
            with open(pcre2_pc, "r") as source_file:
                pcre2_contents = source_file.read()
            with open(libpcre2_pc, "w") as destination_file:
                destination_file.write(
                    pcre2_contents.replace("Name: pcre2", "Name: libpcre2-8")
                )
        if os.path.isdir(self.generators_folder):
            env.append_path("PKG_CONFIG_PATH", self.generators_folder)

    def build(self):
        apply_conandata_patches(self)
        # CI 从 ohpcd 下载的依赖包（glib/pcre2/libffi）自带 .la 文件，
        # 其中记录的被 conan relocatable 打包改坏的绝对路径（//lib/xxx.la）
        # 导致 libtool 链接 libgee-0.8.la 时报
        # "error: '//lib/libpcre2-8.la' is not a valid libtool archive"。
        # 删除依赖 lib 目录下的 *.la（libtool 找不到 .la 时直接用 .so），
        # 与 a52dec/adolc/alsa-lib 等配方清理 .la 的先例一致。
        for dep in self.dependencies.values():
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                for _la in os.listdir(lib_dir):
                    if _la.endswith(".la"):
                        os.remove(os.path.join(lib_dir, _la))
                        self.output.info(f"removed broken libtool archive: {dep.ref}/{_la}")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游官方测试：make check（gtester 运行 tests 测试程序）
        self.run("make check -j1", env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # ⭐ HMDFS 截断修复：本机 install/ginstall 对 ~3MB 的 libgee-0.8.so 报
        # "error deallocating ... Permission denied" 后文件被截断到 ~500KB
        # （ELF section header 越界，消费方链接报 "section header table goes past
        # the end of the file"）。cp/read 正常。用 cp（shutil.copy2）从 build 目录
        # .libs 重新覆盖安装即可。
        _so_real = "libgee-0.8.so.2.6.1"
        _so_src = os.path.join(self.build_folder, "gee", ".libs", _so_real)
        _so_dst = os.path.join(self.package_folder, "lib", _so_real)
        if os.path.isfile(_so_src) and os.path.isfile(_so_dst):
            if os.path.getsize(_so_dst) != os.path.getsize(_so_src):
                shutil.copy2(_so_src, _so_dst)
                self.output.info(
                    "HMDFS ginstall truncated libgee-0.8.so; re-copied "
                    f"{os.path.getsize(_so_dst)} bytes from build .libs"
                )

    def package_info(self):
        self.cpp_info.libs = ["gee-0.8"]
        # 头文件位于 include/gee-0.8（geeincludedir）
        self.cpp_info.includedirs = ["include/gee-0.8"]
        # 传递依赖链：gee-0.8.pc Requires glib-2.0/gobject-2.0，消费方
        # （如 granite）需要 glib 的头文件/库路径（CMakeDeps 场景）
        self.cpp_info.requires = ["glib::glib"]
        self.cpp_info.set_property("pkg_config_name", "gee-0.8")
        self.cpp_info.set_property("cmake_file_name", "libgee")
        self.cpp_info.set_property("cmake_target_name", "libgee::libgee")
