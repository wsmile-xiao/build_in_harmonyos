#!/usr/bin/env python3
"""Conan recipe — libppd 2.1.1 (OpenPrinting PPD library).

libppd 是 OpenPrinting 的 PPD（PostScript Printer Description）
文件处理库，CUPS 3.x 时代的 PPD API 抽离。提供 PPD 文件解析、
属性访问、选项处理等功能，供打印驱动和过滤器使用。

构建：autotools（release tarball 含预生成 configure/Makefile.in）
依赖：cups（通过 cups-config 检测）
许可证：Apache-2.0

OHOS 适配要点：
  1. release tarball 的 config.guess（2022 版）不认识 OHOS，
     需手动 patch config.guess/config.sub 识别 HarmonyOS/OHOS
  2. 显式设 --build/--host=aarch64-ohos-linux-gnu，绕过 config.guess
  3. release tarball 含预生成 configure，无需 autoreconf
     （CI worker 缺 aclocal/autopoint）
"""
import os
import re

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibppdConan(ConanFile):
    name = "libppd"
    version = "2.1.1"
    description = "OpenPrinting PPD file handling library"
    license = "Apache-2.0"
    homepage = "https://github.com/OpenPrinting/libppd"
    url = "https://github.com/OpenPrinting/libppd"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # libppd 通过 cups-config 检测 CUPS 2.x
        self.requires("cups/2.4.19")
        # libppd 2.1.1 configure 硬依赖 libcupsfilters（PKG_CHECK_MODULES）
        self.requires("libcupsfilters/2.2.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 优先走 cups2 fallback 路径（仓库里是 cups 2.4.19）
        tc.configure_args.append("--with-cups-config=cups-config")
        # OHOS 平台：显式指定 build/host，绕过 config.guess 自动检测
        # config.guess 2022 版不认识 OHOS，即使 patch 后也可能误判
        triplet = "aarch64-ohos-linux-gnu"
        tc.configure_args.append(f"--build={triplet}")
        tc.configure_args.append(f"--host={triplet}")
        # OHOS 交叉编译：configure 尝试运行编译出的 conftest 会失败，
        # 用 cache 预设绕过运行测试
        tc.configure_args.append("ac_cv_prog_cc_cross=yes")
        tc.configure_args.append("cross_compiling=yes")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        # 1. Patch configure: umask 077 → 022
        #    OHOS HMDFS 在 umask 077 下创建临时目录得到 2700 权限，
        #    编译器无法访问 conftest.c，导致 configure 编译测试失败。
        #    用 Python replace 直接修改，不依赖行号（比 patch 更可靠）。
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(configure_path, "w") as f:
                    f.write(content)
                self.output.info("  [ok] configure: umask 077 → 022")
            else:
                self.output.info("  [ok] configure: umask 077 not found, skipping")
        # 2. Patch config.guess/config.sub 识别 OHOS（双保险：
        #    即使 --build/--host 指定了，libtool 仍可能调用 config.guess）
        self._patch_config_for_ohos()
        # 3. release tarball 含预生成 configure，直接 configure + make
        autotools = Autotools(self)
        # 不传 args：让 generate() 里 tc.configure_args 的全部参数
        # （--with-cups-config、--build/--host、ac_cv_prog_cc_cross=yes 等）自动生效。
        # 之前传 args=[...] 会覆盖 generate() 的 configure_args，
        # 导致 --with-cups-config 等丢失，configure 用错误参数运行。
        autotools.configure()
        autotools.make()

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub to recognize HarmonyOS/OHOS.

        release tarball 的 config.guess 是 2022 版本，不认识 OHOS。
        参考 addrwatch 1.0.2 的做法，手动 patch 识别 OHOS。
        """
        cg_path = os.path.join(self.source_folder, "config.guess")
        cs_path = os.path.join(self.source_folder, "config.sub")

        if not os.path.exists(cg_path) or not os.path.exists(cs_path):
            self.output.info(
                "config.guess/config.sub not found, skipping OHOS patch"
            )
            return

        self._patch_config_guess(cg_path)
        self._patch_config_sub(cs_path)

    def _patch_config_guess(self, cg_path):
        """Manually patch config.guess for HarmonyOS detection."""
        with open(cg_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add __OHOS__ LIBC detection after __ANDROID__
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = (
                "#if defined(__ANDROID__)\n    LIBC=android\n"
                "#elif defined(__OHOS__)\n    LIBC=ohos"
            )
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
                self.output.info(
                    "  [ok] Added __OHOS__ LIBC detection to config.guess"
                )
            else:
                self.output.warning(
                    "  [warn] Could not find __ANDROID__/LIBC=android in config.guess"
                )

        # 2. Add HarmonyOS case block before NetBSD
        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)          MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace(
                    "    *:NetBSD:*:*)", block, 1
                )
                changed = True
                self.output.info(
                    "  [ok] Added HarmonyOS system identification to config.guess"
                )
            else:
                self.output.warning(
                    "  [warn] Could not find NetBSD insertion point in config.guess"
                )

        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _patch_config_sub(self, cs_path):
        """Manually patch config.sub for ohos-linux support."""
        with open(cs_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add ohos-linux triplet after android-linux
        if "ohos-linux" not in content:
            pattern = (
                r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown'
                r'\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            )
            replacement = (
                r'\1\tohos-linux)\n'
                r'\tbasic_machine=$field1-unknown\n'
                r'\tbasic_os=linux-ohos\n'
                r'\t;;\n'
            )
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True
                self.output.info(
                    "  [ok] Added ohos-linux triplet to config.sub"
                )
            else:
                self.output.warning(
                    "  [warn] Could not find android-linux in config.sub"
                )

        # 2. Add ohos* to OS type list
        if "ohos*" not in content:
            content = content.replace(
                "gnu* | android*", "gnu* | android* | ohos*", 1
            )
            changed = True
            self.output.info("  [ok] Added ohos* to OS list in config.sub")

        # 3. Add linux-ohos to kernel-OS validation list
        if "linux-ohos" not in content:
            content, count = re.subn(
                r'(linux-uclibc[\*/-]?\s*\))',
                r'\1| linux-ohos*)',
                content,
            )
            if count > 0:
                changed = True
                self.output.info(
                    "  [ok] Added linux-ohos to kernel list in config.sub"
                )
            else:
                self.output.warning(
                    "  [warn] Could not find linux-uclibc pattern in config.sub"
                )

        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        autotools = Autotools(self)
        autotools.install()

        # 清理不需要的文件
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libppd")
        self.cpp_info.libs = ["ppd"]
        # libppd 用 --prefix=.../usr 安装，头文件在 usr/include/ppd/
        self.cpp_info.includedirs = ["usr/include"]
        # libppd 需要 libcups + libcupsfilters
        self.cpp_info.requires = ["cups::cups", "libcupsfilters::libcupsfilters"]
