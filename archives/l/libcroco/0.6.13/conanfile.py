#!/usr/bin/env python3
"""Conan recipe — libcroco 0.6.13

libcroco is a standalone CSS2 parsing and manipulation library (GNOME).
Autotools build; requires glib-2.0 and libxml-2.0 (pkg-config).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibcrocoConan(ConanFile):
    name = "libcroco"
    version = "0.6.13"
    description = "Libcroco is a standalone CSS2 parsing and manipulation library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libcroco"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES([CROCO],[glib-2.0 >= 2.0 libxml-2.0 >= 2.4.23])
        self.requires("glib/2.88.0.1")
        self.requires("libxml2/2.15.3.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @property
    def _la_free_dir(self):
        return os.path.join(self.build_folder, "dependency-archives")

    def generate(self):
        # PKG_CHECK_MODULES 依赖 glib-2.0/libxml-2.0 的 .pc 文件
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "libcroco/0.6.13 currently supports only OHOS armv8"
                )
            # 2018 版 config.sub 不认识 aarch64-linux-ohos，0001 补丁已加入
            # linux-ohos 支持；autotools 仍需显式 host/build 三元组。
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

        if str(self.settings.os) == "OHOS":
            la = self._la_free_dir
            glib = self.dependencies["glib"].package_folder
            xml2 = self.dependencies["libxml2"].package_folder
            # E236: 依赖包（pcre2 传递依赖）带不可搬迁的 .la 元数据
            # （libdir='//lib'），libtool 递归打开时失败
            # （"'//lib/libpcre2-8.la' is not a valid libtool archive"）。
            # 与 dbus-glib/0.114 先例一致：只把 .a/.so 复制到无 .la 的
            # 构建私有目录，并通过 CROCO_CFLAGS/CROCO_LIBS 覆盖 pkg-config
            # 输出（configure 对预置 CROCO_* 变量优先，见 configure 中
            # 'if test -n "$CROCO_LIBS"; then pkg_cv_CROCO_LIBS=...'）。
            env = Environment()
            env.define(
                "CROCO_CFLAGS",
                f"-I{os.path.join(glib, 'include')} "
                f"-I{os.path.join(glib, 'include', 'glib-2.0')} "
                f"-I{os.path.join(glib, 'lib', 'glib-2.0', 'include')} "
                f"-I{os.path.join(xml2, 'include', 'libxml2')}",
            )
            env.define(
                "CROCO_LIBS",
                f"-L{la} -lglib-2.0 -lintl -lffi -lpcre2-8 -lpcre2-posix "
                "-lxml2 -lm -lpthread -ldl -lrt",
            )
            env.vars(self, scope="build").save_script("libcroco-deps")

    def build(self):
        apply_conandata_patches(self)

        if str(self.settings.os) == "OHOS":
            # E236 scoped-la-free-static-archive-directory：仅复制依赖 .a
            # 与 .so 到构建私有目录（无 .la 元数据），绝不改动 conan 缓存。
            la = self._la_free_dir
            for dep in ("glib", "pcre2"):
                libdir = os.path.join(self.dependencies[dep].package_folder, "lib")
                copy(self, "*.a", src=libdir, dst=la, keep_path=False)
            copy(self, "libxml2.so*",
                 src=os.path.join(self.dependencies["libxml2"].package_folder, "lib"),
                 dst=la, keep_path=False)
            self.output.info(f"la-free archives: {sorted(os.listdir(la))}")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # E236: 移除最终包内生成的 .la 元数据
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["croco-0.6"]
        self.cpp_info.includedirs = ["include/libcroco-0.6"]
        # 静态消费方需传递 glib/libxml2 链接闭包；pcre2/zlib/libffi 已由
        # glib::glib-2.0 组件自身的 requires 携带（pcre2 非本配方直接依赖，
        # 直接引用会触发 conan 校验错误）。
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "libxml2::libxml2",
        ]
        # 包体含 CLI：csslint-0.6 与 croco-0.6-config（bin/），声明 bindirs
        # 供 R38/L0k 正确识别为 CLI 库（commands.json 已随原子性交付）。
        self.cpp_info.bindirs = ["bin"]