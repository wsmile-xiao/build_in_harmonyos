#!/usr/bin/env python3
"""Conan recipe — fondu 0.0.20060102

fondu 是一组 Macintosh 字体文件转换命令行工具（fondu/ufond/showfond/dfont2res/
tobin/frombin/lumper/setfondname），把 .dfont/.bin/.hqx 等 Mac 字体资源
转换为 UNIX 字体格式（TTF/OTF/PFB/BDF）。

构建系统：autotools（configure.in 极简：AC_INIT + AC_PROG_CC + AC_CANONICAL_HOST）。
依赖：无外部依赖（仅 libc + libm）。
License: BSD-3-Clause（PfaEdit/George Williams）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FonduConan(ConanFile):
    name = "fondu"
    version = "0.0.20060102"
    description = "Convert Macintosh font files to UNIX font format (fondu/ufond/showfond/dfont2res/tobin/frombin/lumper/setfondname)"
    license = "BSD-3-Clause"
    homepage = "https://fondu.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R15: 2006 版 config.guess 无法识别 HarmonyOS 主机的 uname -s，
        # 显式指定三元组（参考 texi2html/bmon PR 做法），config.sub 在
        # build() 内手动 patch 增加 aarch64 CPU 支持后即可通过校验。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_sub_for_ohos()

        # HMDFS 默认 TMPDIR 下 conftest 写 dummy.c 报 Permission denied → 指到稳定可写目录。
        # ⚠️ 用 ~/.conan_build_tmp（持久）而非 build_folder/_tmp：后者会被 conan 在
        #    test_package 阶段前清掉，而 os.environ["TMPDIR"] 泄漏到同进程的 test_package
        #    → 其 clang 找不到该 tmp 目录（No such file）。
        _tmp = os.path.join(os.path.expanduser("~"), ".conan_build_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        # 2006 版 configure 生成的 config.status 用 "umask 077 && mktemp -d ./confstatXXXXXX"
        # 创建临时目录；HMDFS 上该目录 owner 非当前用户且无写权限，导致
        # "can't create ./confstatXXXXXX/subs.sed: Permission denied"。
        # 将 umask 077 改为 022，使临时目录可写（参考 jbig2dec PR 的 umask 处理）。
        self._patch_configure_umask()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _patch_configure_umask(self):
        """Patch configure/config.status 的临时目录 umask 077 → 022（HMDFS 权限修复）。"""
        cfg = os.path.join(self.build_folder, "configure")
        if not os.path.exists(cfg):
            cfg = os.path.join(self.source_folder, "configure")
        if not os.path.exists(cfg):
            self.output.warning("configure not found, skipping umask patch")
            return
        with open(cfg, "r") as f:
            content = f.read()
        if "umask 077" not in content:
            return
        content = content.replace("umask 077 && mktemp -d", "umask 022 && mktemp -d")
        content = content.replace("umask 077 && mkdir $tmp", "umask 022 && mkdir $tmp")
        with open(cfg, "w") as f:
            f.write(content)
        self.output.info("configure: patched config.status tmp dir umask 077 -> 022")

    def _patch_config_sub_for_ohos(self):
        """手动 patch config.sub：2006 版不识别 aarch64 CPU，导致
        --build=aarch64-unknown-linux-gnu 校验失败。添加 aarch64/aarch64_be
        CPU 支持（bare CPU case + company-name case）。
        注：主机无 perl，patch-autotools-ohos.pl 不可用；config.guess 因
        显式 --build 不会被调用，无需 patch。
        """
        cs = os.path.join(self.source_folder, "config.sub")
        if not os.path.exists(cs):
            self.output.warning("config.sub not found, skipping OHOS patch")
            return

        with open(cs, "r") as f:
            content = f.read()
        changed = False

        # 1. bare CPU case：i*86 | x86_64 之前插入 aarch64 | aarch64_be
        if "aarch64" not in content:
            old_bare = "\ti*86 | x86_64)\n\t  basic_machine=$basic_machine-pc\n\t  ;;"
            new_bare = "\taarch64 | aarch64_be)\n\t  basic_machine=$basic_machine-unknown\n\t  ;;\n\t" + old_bare.lstrip("\t")
            if old_bare in content:
                content = content.replace(old_bare, new_bare)
                changed = True

            # 2. company-name case：aarch64-* 加入 CPU 列表。
            # 注意：case 模式列表第一项 580-* 不带 | 前缀，后续项都必须以 | 开头。
            # 在 580-* 之前插入新项时，必须把 580-* 改为 | 580-* 保持语法合法。
            old_comp = "\t580-* \\\n"
            new_comp = "\taarch64-* | aarch64_be-* \\\n\t| 580-* \\\n"
            if old_comp in content:
                content = content.replace(old_comp, new_comp)
                changed = True

        if changed:
            with open(cs, "w") as f:
                f.write(content)
            self.output.info("config.sub: added aarch64/aarch64_be CPU support")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 确保 8 个命令行工具都在 bin/
        bin_dir = os.path.join(self.package_folder, "bin")
        for tool in ("fondu", "ufond", "showfond", "dfont2res", "tobin", "frombin", "lumper", "setfondname"):
            src = os.path.join(self.build_folder, tool)
            if os.path.exists(src):
                copy(self, tool, src=self.build_folder, dst=bin_dir)

    def package_info(self):
        # fondu 是命令行工具集合，不是库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
