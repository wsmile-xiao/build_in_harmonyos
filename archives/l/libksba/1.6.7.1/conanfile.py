#!/usr/bin/env python3
"""Conan recipe — libksba 1.6.7.1 (autotools; upstream libksba 1.6.7 tarball)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout


class LibksbaConan(ConanFile):
    name = "libksba"
    version = "1.6.7.1"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("libgpg-error/1.55")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 设备 HMDFS 上 config.guess 的 mktemp 探针写 dummy.c 报 Permission denied（"unable to guess
        # system type"）。显式给 --build/--host 直接跳过 config.guess（config.sub 纯 shell、不编译，
        # libksba 1.6.7 自带 linux-musl* 分支）。build==host → 原生模式。
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-doc")
        # 只出共享库（test_package 走 dlopen 探针）。
        tc.configure_args.append("--disable-static")
        tc.configure_args.append("--with-libgpg-error-prefix={}".format(self.dependencies["libgpg-error"].package_folder))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import glob, os
        # 设备默认 TMPDIR(/storage/.../tmp, HMDFS) 上 conftest/config.guess 写 dummy.c 报 Permission
        # denied → 指到 conan build 目录（可写可执行）。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        # gpg-error.m4 用 AC_PATH_PROG 在 PATH 上找 gpgrt-config，--with-libgpg-error-prefix 的
        # $prefix/bin/gpg-error-config 在 libgpg-error 1.55 已不存在（换成 gpgrt-config）。
        # 把 libgpg-error 的 bin 加进 PATH，m4 命中 gpgrt-config 后反推 prefix 检测 gpg-error.pc。
        _gpgerr = self.dependencies["libgpg-error"].package_folder
        os.environ["PATH"] = os.path.join(_gpgerr, "bin") + os.pathsep + os.environ.get("PATH", "")
        # gpgrt-config --cflags 为空（includedir 按烤死的 / 算成标准路径）→ 编译找不到 gpg-error.h。
        # 直接经 CPPFLAGS/LDFLAGS 补 libgpg-error 的 include/lib（autoconf 会把它烤进 Makefile）。
        os.environ["CPPFLAGS"] = "-I{} ".format(os.path.join(_gpgerr, "include")) + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = "-L{} ".format(os.path.join(_gpgerr, "lib")) + os.environ.get("LDFLAGS", "")
        # 归档目录会按 077 建含 0600 成员，CI worker 上 install 阶段拷贝可读即可，但放宽 umask 更稳
        # （与 libgpg-error/libgcrypt/libpq 一致）。
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游回归套件（rule4 须实跑；7 个 test 二进制在 make all 阶段已编好，
        # make check 在本机 musl 上运行，sample 数据随源码包分发）。
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        explicit_libs = ['ksba']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "libksba")
        self.cpp_info.set_property("cmake_target_name", "libksba::libksba")
        self.cpp_info.set_property("pkg_config_name", "ksba")
