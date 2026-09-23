#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Cloog, cloog, 0.21.1, cloog 0.21.1, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class CloogConan(ConanFile):
    name = "cloog"
    version = "0.21.1"
    description = "CLooG - Chunky Loop Generator, polyhedral code generation library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/periscop/cloog"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("isl25/0.25")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Use system gmp and isl, bundled osl
        gmp_root = self.dependencies["gmp"].package_folder
        isl_root = self.dependencies["isl25"].package_folder
        tc.configure_args.append("--with-gmp=system")
        tc.configure_args.append(f"--with-gmp-prefix={gmp_root}")
        tc.configure_args.append("--with-isl=system")
        tc.configure_args.append(f"--with-isl-prefix={isl_root}")
        tc.configure_args.append("--with-osl=bundled")
        tc.configure_args.append("--with-cloog-int=gmp")
        # 保留显式 --build/--host：cloog 0.21.1 的 config.guess 是 2021 新版
        # （GUESS= 变量格式，_patch_ohos_compat 的 aarch64:Linux OHOS case 已生效），
        # 原始 CI 日志确认 configure 通过（失败仅在 test_package 的 gmp.h）——
        # 记忆里 "--build 致 C compiler cannot create executables" 针对旧版
        # config.guess（2007 格式，skymaker 等），此处移除反而致 cannot guess build type
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()
        # Set TMPDIR to build folder so config.guess can write temp files on HMDFS
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        envvars = env.vars(self)
        envvars.save_script("conantmpdir")

    def build(self):
        apply_conandata_patches(self)
        self._patch_ohos_compat()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _patch_ohos_compat(self):
        """Patch config.guess/sub/configure for OHOS and HMDFS compatibility."""
        import os

        # Fix broken .la dependency paths in conan packages (isl25 has //lib/libgmp.la)
        gmp_root = self.dependencies["gmp"].package_folder
        for root, dirs, files in os.walk(self.dependencies["isl25"].package_folder):
            for name in files:
                if name.endswith(".la"):
                    la_path = os.path.join(root, name)
                    try:
                        with open(la_path, "r") as f:
                            la_content = f.read()
                        if "//lib/" in la_content:
                            la_content = la_content.replace("//lib/", f"{gmp_root}/lib/")
                            with open(la_path, "w") as f:
                                f.write(la_content)
                    except (PermissionError, IsADirectoryError):
                        pass

        for root, dirs, files in os.walk(self.source_folder):
            for name in files:
                path = os.path.join(root, name)
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except (PermissionError, IsADirectoryError):
                    continue
                changed = False

                if name in ("config.sub", "config.guess"):
                    # config.sub: add ohos to OS validity list
                    old1 = '| nsk* | powerunix* | genode* | zvmoe* | qnx* | emx* | zephyr*)'
                    if old1 in content and 'ohos*)' not in content:
                        content = content.replace(old1, old1.replace('zephyr*)', 'zephyr* \\\n\t     | ohos*)'), 1)
                        changed = True
                    # config.sub: add linux-ohos to kernel-os validation
                    old2 = 'linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\\n\t\t   | linux-musl* | linux-relibc* | linux-uclibc* )'
                    if old2 in content and 'linux-ohos*' not in content:
                        content = content.replace(old2, old2.replace('linux-uclibc* )', 'linux-uclibc* | linux-ohos* )'), 1)
                        changed = True
                    # config.guess: add OHOS detection for aarch64
                    old3 = '    aarch64:Linux:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-$LIBC\n\t;;'
                    new3 = '    aarch64:Linux:*:*)\n\tcase `uname` in\n\t  *OHOS*) GUESS=$UNAME_MACHINE-unknown-linux-ohos ;;\n\t  *) GUESS=$UNAME_MACHINE-unknown-linux-$LIBC ;;\n\tesac\n\t;;'
                    if old3 in content and 'OHOS' not in content:
                        content = content.replace(old3, new3, 1)
                        changed = True

                if name == "configure":
                    # HMDFS: mktemp creates dirs with drwx--S--- that chmod can't fix
                    old_mktemp = '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"\n}  ||\n{\n  tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")'
                    new_mkdir = '  tmp=./conf$$-$RANDOM\n  mkdir -p -m 755 "$tmp" && test -d "$tmp"'
                    if old_mktemp in content:
                        content = content.replace(old_mktemp, new_mkdir, 1)
                        changed = True

                if changed:
                    with open(path, "w") as f:
                        f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # cloog 用 --with-osl=bundled，包内含 libcloog-isl.a + libosl.a；
        # libcloog-isl 引用 osl_scop_free 等 OSL 符号，消费者链接必须同时链 libosl
        self.cpp_info.libs = ["cloog-isl", "osl"]
        # 传递 gmp/isl 依赖：cloog 公共头 cloog/int.h 直接 #include <gmp.h>，
        # 消费者（test_package）编译时必须拿到 gmp/isl 的 include/lib 路径
        self.cpp_info.requires = ["gmp::gmp", "isl25::isl25"]
        # gmp 包自身 CMakeDeps 数据 gmp_INCLUDE_DIRS_RELEASE 为空（gmp 为已发布包，
        # include 路径未进其 CMakeDeps 数据），仅靠 requires 传递拿不到 gmp.h——
        # 显式把依赖 include 目录加进 cpp_info，保证消费者编译 cloog.h→int.h→gmp.h 可解析
        gmp_root = self.dependencies["gmp"].package_folder
        isl_root = self.dependencies["isl25"].package_folder
        self.cpp_info.includedirs.append(os.path.join(gmp_root, "include"))
        self.cpp_info.includedirs.append(os.path.join(isl_root, "include"))
