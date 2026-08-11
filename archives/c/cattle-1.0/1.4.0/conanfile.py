#!/usr/bin/env python3
"""Conan recipe — cattle-1.0 1.4.0（Brainfuck 语言工具包）.

Cattle 是基于 GObject 的 Brainfuck 编程语言工具包，可嵌入应用
以检查/运行 Brainfuck 程序。
构建系统：GNU Autotools（官方 tarball 已预生成 configure）
平台：OHOS aarch64 / Linux / macOS
依赖：glib（glib-2.0/gobject-2.0/gio-2.0 >= 2.38）
"""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, Autotools, PkgConfigDeps
from conan.tools.layout import basic_layout


class CattleConan(ConanFile):
    name = "cattle-1.0"
    version = "1.4.0"
    description = "Cattle — Brainfuck language toolkit (GObject-based)"
    license = "GPL-2.0-or-later"
    homepage = "https://kiyuko.org/software/cattle"
    url = "https://github.com/andreabolognani/cattle"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")

    def layout(self):
        # cattle configure 要求 out-of-source 构建（build 目录 ≠ source 目录），
        # basic_layout 将 build 与 source 分离，Autotools 在 build 目录运行
        # configure 指向 source 目录的 configure 脚本
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _machine(self, arch):
        # 从 arch setting 推导 GNU 三元组 machine 部分
        return {
            "armv8": "aarch64",
            "armv7": "arm",
            "x86_64": "x86_64",
            "x86": "i686",
        }.get(str(arch), str(arch))

    def generate(self):
        # 生成 glib 依赖的 .pc 文件并注入 PKG_CONFIG_PATH（cattle configure
        # 用 pkg-config 查找 glib-2.0/gobject-2.0/gio-2.0）
        PkgConfigDeps(self).generate()
        # gobject-2.0.pc/gio-2.0.pc 位于 glib 依赖包内的 lib/pkgconfig/
        # （PkgConfigDeps 仅生成 glib-2.0.pc），追加该目录到 PKG_CONFIG_PATH；
        # glib 包的 bin/ 加入 PATH（cattle 生成 cattle-enums 需要 glib-mkenums 工具）
        env = Environment()
        glib_pkg = self.dependencies["glib"].package_folder
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(glib_pkg, "lib", "pkgconfig"))
        env.prepend_path("PATH", os.path.join(glib_pkg, "bin"))
        env.vars(self).save_script("conanbuild_pkgconfig")
        tc = AutotoolsToolchain(self)
        # 按 shared 选项设置 autotools 构建类型（默认静态）
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        # cattle 的 config.guess（2018-02-24）无法识别 HarmonyOS
        # （uname -s=HarmonyOS），指定 --build/--host 三元组跳过检测
        machine = self._machine(self.settings.arch)
        triplet = f"{machine}-unknown-linux-gnu"
        tc.configure_args.extend([f"--build={triplet}", f"--host={triplet}"])
        tc.generate()

    def _fix_glib_la_paths(self):
        """修正 glib 依赖链 .la 文件的 dependency_libs 路径（//lib/ → 实际缓存路径）.

        ohpcd 二进制包构建时 prefix=/ 导致 .la 文件 dependency_libs 记录
        //lib/ 错误路径，libtool 递归解析依赖时找不到 .la 报
        "not a valid libtool archive"（CI #16082，libcattle-1.0.la 链接失败）。
        """
        import glob

        for dep_name in ("glib", "libffi", "pcre2"):
            try:
                dep = self.dependencies[dep_name]
            except (KeyError, AttributeError):
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for la_path in glob.glob(os.path.join(lib_dir, "*.la")):
                with open(la_path, "r") as f:
                    content = f.read()
                new_content = content.replace("//lib/", f"{lib_dir}/")
                if new_content != content:
                    with open(la_path, "w") as f:
                        f.write(new_content)
                    self.output.info(f"fixed la paths in {la_path}")

    def build(self):
        # OHOS 沙箱 umask 077 导致 config.status 创建的 0700 临时目录不可写
        # （confljklah/subs1.awk Permission denied），临时改 umask 022
        # （opensp/ncurses 先例），try/finally 恢复
        autotools = Autotools(self)
        old_umask = os.umask(0o022)
        try:
            # 修正 glib 依赖链 .la 文件路径（ohpcd 二进制包 //lib/ 错误路径，
            # libtool 链接 libcattle-1.0.la 时解析失败）
            self._fix_glib_la_paths()
            # CC/CXX 由 Conan 工具链（tools.build:compiler_executables）注入，
            # configure 直接运行（官方 tarball 预生成 configure，免 autoreconf）。
            # make 使用 -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败
            # （opensp 先例）
            autotools.configure()
            autotools.make(args=["-j1"])

            # 仅在 native 编译时运行上游测试（tests/ 目录）
            if not cross_building(self):
                autotools.make(target="check", args=["-j1"])
        finally:
            os.umask(old_umask)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include/cattle-1.0"]
        self.cpp_info.libs = ["cattle-1.0"]
        self.cpp_info.set_property("pkg_config_name", "cattle-1.0")
        self.cpp_info.set_property("cmake_file_name", "cattle-1.0")
        self.cpp_info.set_property("cmake_target_name", "cattle-1.0::cattle-1.0")