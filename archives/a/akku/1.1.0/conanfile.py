#!/usr/bin/env python3
"""Conan recipe for akku 1.1.0 — Scheme 语言包管理器（Autotools）。

Build system: Autotools (configure + make)。
核心依赖：guile（GUILE_PKG/GUILE_PROGS 检查，需要 guild 二进制与
guile-2.2.pc pkg-config 文件）。OHOS 无 texinfo/makeinfo，用 fake
makeinfo 跳过文档生成（同 guile 配方）。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class AkkuConan(ConanFile):
    name = "akku"
    version = "1.1.0"
    description = "Akku.scm - package manager for Scheme"
    license = "GPL-3.0-or-later"
    homepage = "https://akkuscm.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 裸格式引用（ohpcd 制品仓无 user/channel）
        self.requires("guile/2.2.7.1")
        # akku 的 HTTP client 运行时通过 Guile FFI dlopen libcurl.so.4。
        self.requires("curl/8.15.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-dependency-tracking")
        # OHOS 无 texinfo/makeinfo：安装 doc 时 make 尝试重建 info 报
        # Error 127。用 fake makeinfo 生成空 info 文件跳过文档生成。
        fake_bin = os.path.join(self.build_folder, "fake-bin")
        os.makedirs(fake_bin, exist_ok=True)
        fake_makeinfo = os.path.join(fake_bin, "makeinfo")
        with open(fake_makeinfo, "w") as fh:
            fh.write("#!/bin/sh\n"
                     'out=""\n'
                     'prev=""\n'
                     'for arg in "$@"; do\n'
                     '  if [ "$prev" = "-o" ]; then out="$arg"; fi\n'
                     '  prev="$arg"\n'
                     'done\n'
                     '[ -n "$out" ] && touch "$out"\n'
                     "exit 0\n")
        os.chmod(fake_makeinfo, 0o755)
        # 先追加完 flags 再取 environment()（环境快照才包含这些值）
        guile_dep = self.dependencies.get("guile")
        guile_pkg_config_dir = None
        guile_cflags = []
        guile_libs = []
        if guile_dep:
            for inc in guile_dep.cpp_info.includedirs:
                cflag = f"-I{inc}"
                tc.extra_cflags.append(cflag)
                guile_cflags.append(cflag)
            for libdir in guile_dep.cpp_info.libdirs:
                tc.extra_ldflags.append(f"-L{libdir}")
                tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")
                guile_libs.extend([f"-L{libdir}", "-lguile-2.2"])
                pkg_dir = os.path.join(libdir, "pkgconfig")
                if os.path.isdir(pkg_dir):
                    guile_pkg_config_dir = pkg_dir
        env = tc.environment()
        env.define("MAKEINFO", fake_makeinfo)
        if guile_dep:
            # GUILE_PKG 用 pkg-config 检查 guile-2.2.pc
            if guile_pkg_config_dir:
                env.append_path("PKG_CONFIG_PATH", guile_pkg_config_dir)
            # OHOS runner 不保证有 pkg-config；上游 configure 只需要
            # pkg-config 确认 guile-2.2 存在，后续工具路径由 GUILE_PROGS 查找。
            fake_pkg_config = os.path.join(fake_bin, "pkg-config")
            with open(fake_pkg_config, "w") as fh:
                fh.write(
                    "#!/bin/sh\n"
                    'case " $* " in\n'
                    '*" --atleast-pkgconfig-version "*) exit 0 ;;\n'
                    "esac\n"
                    'pkg=""\n'
                    'for arg in "$@"; do\n'
                    '  [ "$arg" = "guile-2.2" ] && pkg="guile-2.2"\n'
                    '  [ "$arg" = "guile-3.0" ] && exit 1\n'
                    "done\n"
                    '[ "$pkg" = "guile-2.2" ] || exit 1\n'
                    'for arg in "$@"; do\n'
                    '  case "$arg" in\n'
                    '    --exists) exit 0 ;;\n'
                    '    --modversion|--version) echo "2.2.7"; exit 0 ;;\n'
                    f'    --cflags) echo "{" ".join(guile_cflags)}"; exit 0 ;;\n'
                    f'    --libs) echo "{" ".join(guile_libs)}"; exit 0 ;;\n'
                    "  esac\n"
                    "done\n"
                    "exit 0\n"
                )
            os.chmod(fake_pkg_config, 0o755)
            env.define("PKG_CONFIG", fake_pkg_config)
            env.append_path("PATH", fake_bin)
            # GUILE_PROGS 需要 guild 二进制在 PATH
            bin_dir = os.path.join(guile_dep.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.append_path("PATH", bin_dir)
                # guile 的 guild 脚本用 ${GUILE:-//bin/guile} 回退，
                # 安装前缀 / 使回退路径无效，必须显式指定 GUILE
                guile_bin = os.path.join(bin_dir, "guile")
                if os.path.isfile(guile_bin):
                    env.define("GUILE", guile_bin)
            # guild 编译 .go 需要 language/bytecode 等模块：设置
            # GUILE_LOAD_PATH 指向 guile 包的 share/guile/2.2
            # （否则 "no such language bytecode"）
            share_dir = os.path.join(guile_dep.package_folder, "share", "guile", "2.2")
            if os.path.isdir(share_dir):
                env.append_path("GUILE_LOAD_PATH", share_dir)
            ccache_dir = os.path.join(guile_dep.package_folder, "lib", "guile", "2.2", "ccache")
            if os.path.isdir(ccache_dir):
                # guile 2.2 用 GUILE_LOAD_COMPILED_PATH 查找 .go 字节码
                # （GUILE_CCACHE_DIR 是 guile 3.0 变量，2.2 下无效导致
                #  "no such language bytecode"）
                env.append_path("GUILE_LOAD_COMPILED_PATH", ccache_dir)
                env.append_path("GUILE_CCACHE_DIR", ccache_dir)
            # configure 会运行 guile 二进制检查版本，运行时需要
            # libguile-2.2.so.1 在 LD_LIBRARY_PATH（否则
            # "Error loading shared library libguile-2.2.so.1"）
            for libdir in guile_dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
        # OHOS 上 guile 2.2 自动编译（auto-compilation）会触发
        # "no code for module (ice-9 optargs)" / "Unbound variable:
        # compile-file" 等失败。ccache 已有预编译 .go，禁用自动编译
        # 让 guild 直接使用 ccache 字节码。
        env.define("GUILE_AUTO_COMPILE", "0")
        # CI profile 可能注入当前真机不存在的 bash 路径；configure 必须
        # 通过可用的 POSIX shell 运行。
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        configure_path = os.path.join(self.build_folder, "configure")
        if not os.path.isfile(configure_path):
            configure_path = os.path.join(os.path.dirname(self.build_folder), "configure")
        configure_path = unix_path(self, configure_path)
        self.run(
            f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "{configure_path}" '
            f"--prefix=/ "
            f"'--bindir=${{prefix}}/bin' "
            f"'--sbindir=${{prefix}}/bin' "
            f"'--libdir=${{prefix}}/lib' "
            f"'--includedir=${{prefix}}/include' "
            f"'--oldincludedir=${{prefix}}/include' "
            f"--disable-dependency-tracking",
            env="conanbuild",
        )
        autotools = Autotools(self)
        autotools.make(args=["-j1", "SHELL=/bin/sh"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["SHELL=/bin/sh"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            self.runenv_info.append_path("PATH", bin_dir)
            self.buildenv_info.append_path("PATH", bin_dir)
        # akku 自身 Scheme 模块（industria/akku 等）在
        # share/akku/guile/site/2.2；运行时 akku 二进制需要
        # GUILE_LOAD_PATH 指向该目录，否则 "no code for module
        # (industria strings)"。
        site_dir = os.path.join(self.package_folder, "share", "akku", "guile", "site", "2.2")
        if os.path.isdir(site_dir):
            self.runenv_info.append_path("GUILE_LOAD_PATH", site_dir)
            self.buildenv_info.append_path("GUILE_LOAD_PATH", site_dir)
        ccache_dir = os.path.join(self.package_folder, "lib", "akku", "guile", "2.2", "site-ccache")
        if os.path.isdir(ccache_dir):
            self.runenv_info.append_path("GUILE_LOAD_COMPILED_PATH", ccache_dir)
            self.buildenv_info.append_path("GUILE_LOAD_COMPILED_PATH", ccache_dir)
        self.runenv_info.define("GUILE_AUTO_COMPILE", "0")
        self.buildenv_info.define("GUILE_AUTO_COMPILE", "0")
        guile_bin = os.path.join(self.package_folder, "bin", "akku")
        if os.path.isfile(guile_bin):
            self.runenv_info.define("AKKU", guile_bin)
            self.buildenv_info.define("AKKU", guile_bin)
