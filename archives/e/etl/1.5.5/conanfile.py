#!/usr/bin/env python3
"""Conan recipe for ETL (Extended Template Library) 1.5.5.

ETL is a header-only C++ template library from the Synfig project.
It provides smart pointers (handle) and other utility templates
that complement the C++ Standard Template Library (STL).

Since ETL is header-only, this recipe uses the Autotools build system
to run configure + make install which installs the header files
and generates etl_profile.h from etl_profile_.h.in.

Homepage: http://synfig.org/
Source:    https://github.com/synfig/synfig
License:   GPL-3.0-or-later
"""

from conan import ConanFile
from conan.tools.files import (
    get, export_conandata_patches, apply_conandata_patches, patch as conan_patch,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class EtlConan(ConanFile):
    name = "etl"
    version = "1.5.5"
    description = "Extended Template Library -- a C++ STL complementary multiplatform template library from the Synfig project"
    license = "GPL-3.0-or-later"
    homepage = "http://synfig.org/"
    url = "https://github.com/synfig/synfig"

    package_type = "header-library"

    # R32: settings.os must be checked in ("Linux", "OHOS") -- here we declare
    # the full settings so the recipe works on both Linux and OHOS targets.
    settings = "os", "compiler", "build_type", "arch"

    # Header-only library: no shared/static options needed
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)
        # 显式导出 patches/ 目录（conandata patches 可能被 finish 回滚）
        from conan.tools.files import copy
        patches_dir = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(patches_dir):
            copy(self, "*.patch", patches_dir, self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def package_id(self):
        # Header-only library: the package ID is independent of
        # compiler, build_type, and arch.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 原地修补 config.guess/config.sub 识别 HarmonyOS/OHOS
        # （不依赖 conandata patches，避免被 finish 镜像注入回滚）
        self._patch_config_for_ohos()

    def _patch_config_for_ohos(self):
        """Patch config.guess/config.sub in-place to recognize HarmonyOS/OHOS.

        ETL 1.5.5 ships config.guess (2016-10-02) that doesn't know HarmonyOS.
        We normalize UNAME_SYSTEM from HarmonyOS to Linux so the existing
        aarch64:Linux:*:*) branch outputs aarch64-unknown-linux-gnu.
        """
        cg = os.path.join(self.source_folder, "config", "config.guess")
        cs = os.path.join(self.source_folder, "config", "config.sub")

        # config.guess: add HarmonyOS alias to Linux|GNU|GNU/* case
        if os.path.isfile(cg):
            with open(cg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "HarmonyOS" not in content:
                old = "Linux|GNU|GNU/*)\n\t# If the system lacks a compiler, then just pick glibc."
                new = ("Linux|GNU|GNU/*|HarmonyOS)\n"
                       "\t# HarmonyOS: normalize UNAME_SYSTEM to Linux\n"
                       "\tcase \"${UNAME_SYSTEM}\" in HarmonyOS) UNAME_SYSTEM=Linux;; esac\n"
                       "\t# If the system lacks a compiler, then just pick glibc.")
                if old in content:
                    content = content.replace(old, new, 1)
                    with open(cg, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.output.info("Patched config.guess for HarmonyOS")

        # config.sub: add linux-ohos* to maybe_os and basic_machine os lists
        if os.path.isfile(cs):
            with open(cs, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "linux-ohos" not in content:
                # maybe_os list
                content = content.replace(
                    "linux-musl* | linux-uclibc* | uclinux-uclibc*",
                    "linux-musl* | linux-uclibc* | linux-ohos* | uclinux-uclibc*",
                    1,
                )
                # basic_machine os list
                content = content.replace(
                    "| -linux-newlib* | -linux-musl* | -linux-uclibc* \\",
                    "| -linux-newlib* | -linux-musl* | -linux-uclibc* | -linux-ohos* \\",
                    1,
                )
                with open(cs, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info("Patched config.sub for HarmonyOS")

        # configure & config.status: fix mktemp -d "./confXXXXXX" permission
        # OHOS mktemp -d creates dir with mode 2700 (setgid + owner-only),
        # so subsequent echo > "$ac_tmp/subs1.awk" fails with Permission denied.
        # Fix: chmod 755 the mktemp dir right after creation.
        for cfg in (os.path.join(self.source_folder, "configure"),
                    os.path.join(self.source_folder, "config.status")):
            if not os.path.isfile(cfg):
                continue
            with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            old_mktemp = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
            new_mktemp = (
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
                ' chmod 755 "$tmp" &&'
            )
            if old_mktemp in content and "chmod 755" not in content:
                content = content.replace(old_mktemp, new_mktemp, 1)
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"Patched {os.path.basename(cfg)} mktemp permission")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # AutotoolsToolchain automatically passes --build/--host as needed.
        # ETL is header-only; no extra configure args required.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # ⭐ configure 之前修补 configure 脚本的 mktemp 段。
        # OHOS HMDFS 硬性设 mktemp -d 目录为 2700（无 group 权限）且忽略 chmod，
        # 导致 config.status 的 echo > "$ac_tmp/subs1.awk" Permission denied。
        # mkdir 在 OHOS 给 2710（group r-x），可写入。
        # 必须在 configure 之前修补：configure 内部生成并运行 config.status，
        # 修补太晚（configure 之后）来不及——config.status 在第一次运行时就失败。
        self._patch_configure_mktemp()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # ETL is header-only: make check is a no-op (no test binaries)
        # but we run it for completeness per SKILL requirements.
        autotools.make(target="check", args=["-j1"])

    def _patch_configure_mktemp(self):
        """Patch umask 077 -> 022 in configure/config.guess/config.sub.

        OHOS HMDFS 在 umask 077 下用 mktemp -d / mkdir 创建目录时硬性剥夺
        group 权限（得到 2700），导致后续写入（config.status 的 subs1.awk、
        config.guess 的 dummy.c）Permission denied。

        三个文件都要修：
        - configure: mktemp -d "./confXXXXXX" 段 + mkdir "$tmp" 段
        - config.guess: mktemp -d "$TMPDIR/cgXXXXXX" 段 + mkdir $tmp 段
        - config.sub: 同 config.guess

        umask 022 让 mkdir 得到 2710（group r-x），可写入。
        """
        targets = [
            os.path.join(self.source_folder, "configure"),
            os.path.join(self.source_folder, "config", "config.guess"),
            os.path.join(self.source_folder, "config", "config.sub"),
        ]
        for tgt in targets:
            if not os.path.isfile(tgt):
                continue
            with open(tgt, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            changed = False
            # 通用：把所有 "(umask 077 && " 替换为 "(umask 022 && "
            # 这覆盖 configure/config.guess/config.sub 里所有临时目录创建段
            if "(umask 077 && " in content:
                content = content.replace("(umask 077 && ", "(umask 022 && ")
                changed = True
            if changed:
                with open(tgt, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(
                    f"Patched {os.path.basename(tgt)}: umask 077 -> 022 (OHOS 2700 fix)"
                )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # ETL 的 Makefile.am 把头文件装到 include/ETL/ETL/（双层 ETL），
        # 但消费者用 #include <ETL/handle>（单层）。扁平化布局：
        # 把 include/ETL/ETL/* 移到 include/ETL/*，让单层 #include 生效。
        import shutil
        inc_etl = os.path.join(self.package_folder, "include", "ETL")
        nested = os.path.join(inc_etl, "ETL")
        if os.path.isdir(nested):
            for item in os.listdir(nested):
                src = os.path.join(nested, item)
                dst = os.path.join(inc_etl, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)
            os.rmdir(nested)
            self.output.info("Flattened ETL include layout (removed nested ETL/ETL)")

    def package_info(self):
        # Header-only library: no libs to link
        self.cpp_info.libs = []
        # Set include directory so consumers can #include <ETL/handle>
        self.cpp_info.includedirs = ["include"]
