#!/usr/bin/env python3
"""Conan recipe — mmv 2.10 (upstream v2.10) — Autotools build system.

mmv is a program to move/copy/link multiple files according to a set of
wildcard patterns. This multiple action is performed safely.
Source: https://github.com/rrthomas/mmv
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class MmvConan(ConanFile):
    name = "mmv"
    version = "2.10"
    description = "Move, copy, append, and link multiple files with wildcard patterns"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/rrthomas/mmv"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mmv supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # 参照 bash 库做法：仅指定 --build=aarch64-unknown-linux-gnu（config.sub 可接受），
        # 不传 --host（默认 host==build），native 编译模式使 make check 可正常运行。
        # 不使用 --host=ohos，因为 config.sub 不认识 linux-ohos kernel-OS 组合。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # Disable gcc-warnings to avoid build failures from strict warnings
        tc.configure_args.append("--disable-gcc-warnings")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os in ("OHOS",):
            src = self.source_folder
            # E007: 手动 patch config.guess/config.sub 以识别 HarmonyOS/OHOS
            # (不依赖系统 automake 路径，跨 CI Worker 稳定)
            self._patch_config_for_ohos(src)
            configure_path = os.path.join(src, "configure")
            # E165: Fix shebang (no /bin/sh on OHOS)
            replace_in_file(self, configure_path, "#! /bin/sh", "#!/system/bin/sh")
            # E110: Fix umask 077->002 for HMDFS temp directory creation
            replace_in_file(self, configure_path, "umask 077", "umask 002")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1c: 运行上游官方测试 (make check)，mmv 的 make check 运行 gnulib 模块测试
        autotools.make(target="check")

    def _patch_config_for_ohos(self, src):
        """Patch config.guess/config.sub 识别 HarmonyOS/OHOS (E007)。"""
        import re
        build_aux = os.path.join(src, "build-aux")
        cg_path = os.path.join(build_aux, "config.guess")
        cs_path = os.path.join(build_aux, "config.sub")

        # config.guess: 添加 HarmonyOS 系统识别
        if os.path.exists(cg_path):
            with open(cg_path, "r") as f:
                content = f.read()
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
                    content = content.replace("    *:NetBSD:*:*)", block, 1)
                    with open(cg_path, "w") as f:
                        f.write(content)
                    self.output.info("Patched config.guess for HarmonyOS")
                else:
                    self.output.warning("Could not find NetBSD insertion point in config.guess")

        # config.sub: 添加 ohos OS 支持
        if os.path.exists(cs_path):
            with open(cs_path, "r") as f:
                content = f.read()
            changed = False
            # 添加 ohos* 到 OS 类型列表
            if "ohos*" not in content:
                content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
                changed = True
            # 添加 ohos-linux triplet (在 android-linux 之后)
            if "ohos-linux" not in content:
                pattern = r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
                replacement = r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n\tbasic_os=linux-ohos\n\t;;\n'
                content, count = re.subn(pattern, replacement, content)
                if count > 0:
                    changed = True
            # 添加 linux-ohos 到 kernel-OS 校验列表
            if "linux-ohos" not in content:
                content, count = re.subn(r'(linux-uclibc[\*/-]?\s*)\)', r'\1| linux-ohos*)', content)
                if count > 0:
                    changed = True
            if changed:
                with open(cs_path, "w") as f:
                    f.write(content)
                self.output.info("Patched config.sub for ohos")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # mmv is a CLI binary application, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
