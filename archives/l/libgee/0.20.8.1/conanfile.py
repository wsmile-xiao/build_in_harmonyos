#!/usr/bin/env python3
"""Conan recipe for libgee 0.20.8 — GObject collection library (Autotools).

Build system: Autotools (configure + make)。
核心依赖：glib（PKG_CHECK_MODULES 检查 glib-2.0/gobject-2.0/gio-2.0 >= 2.36）。
官方 tarball 自带预生成的 .c 文件与 vala stamp（gee/libgee_0_8_la_vala.stamp、
tests/tests_vala.stamp），VALA_CHECK 检测到 checkfile 存在 → enable_vala=no，
构建不需要 valac；GOBJECT_INTROSPECTION_CHECK 默认 auto，OHOS 无 GI 时自动降级。
config.guess/config.sub 需加 HarmonyOS → aarch64-unknown-linux-ohos 支持（补丁 0001/0002）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibgeeConan(ConanFile):
    name = "libgee"
    version = "0.20.8.1"
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
            # glib/2.84.0.1 起静态内嵌 pcre2/libffi（vendor），这些 Skipped
            # binaries 无 package_folder（None），必须跳过，否则 generate()
            # / build() 直接 TypeError 崩溃（granite-6.2.0 run 实测）
            if not dep.package_folder:
                continue
            for inc in dep.cpp_info.includedirs:
                tc.extra_cflags.append(f"-I{inc}")
            for libdir in dep.cpp_info.libdirs:
                tc.extra_ldflags.append(f"-L{libdir}")
                tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")
                # linkfix: rpath-link 让 ld.lld 在 DT_NEEDED 闭包查找时可定位
                tc.extra_ldflags.append(f"-Wl,-rpath-link,{libdir}")
            # linkfix: g_libintl_* 仅由 glib 包 lib/libintl.so 定义且不在 conan
            # 依赖闭包内，作为显式链接输入注入（granite _augment_glib_intl_
            # pkg_config 同因同款，显式输入在任意 lld 语义下都满足
            # --no-allow-shlib-undefined）。注意必须在 env = tc.environment()
            # 快照之前追加，否则不落 LDFLAGS（fixA2 实测）
            intl = os.path.join(dep.package_folder, "lib", "libintl.so")
            if os.path.isfile(intl):
                tc.extra_ldflags.append(intl.replace(os.sep, "/"))
            else:
                self.output.info(f"linkfix: {dep.ref} has no lib/libintl.so, skip intl input")
        env = tc.environment()
        for dep in self.dependencies.values():
            # glib/2.84.0.1 起静态内嵌 pcre2/libffi（vendor），这些 Skipped
            # binaries 无 package_folder（None），必须跳过，否则 generate()
            # / build() 直接 TypeError 崩溃（granite-6.2.0 run 实测）
            if not dep.package_folder:
                continue
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
            # glib/2.84.0.1 起静态内嵌 pcre2/libffi（vendor），这些 Skipped
            # binaries 无 package_folder（None），必须跳过，否则 generate()
            # / build() 直接 TypeError 崩溃（granite-6.2.0 run 实测）
            if not dep.package_folder:
                continue
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
