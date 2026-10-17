#!/usr/bin/env python3
"""Conan recipe — speex 1.2.1 (autotools).
"""
import os
import shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpeexConan(ConanFile):
    name = "speex"
    version = "1.2.1"
    description = "Audio codec designed for voice encoding over IP networks"
    license = "BSD-3-Clause"
    homepage = "https://speex.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libogg/1.3.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # ⭐ 显式交叉编译模式（asterisk-srtp 同款方案）：不传 --build/--host 时
        # configure 按 native 模式运行，CI 沙箱（hishell_hap 域）禁止运行 conftest
        # 可执行文件 → "checking whether the C compiler works... no"。指定
        # --build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos 后
        # AC_TRY_RUN 全部跳过运行，配合 ac_cv_prog_cc_works=yes 双保险。
        tc.configure_args.append("--build=x86_64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # CI worker 沙箱（hishell_hap 域）禁止生成/运行 conftest 可执行文件
        # → "checking whether the C compiler works... no"（asterisk-srtp 17 轮
        # CI 失败同根因）。ac_cv_prog_cc_works=yes 强制跳过该运行检查
        # （交叉编译模式下 AC_TRY_RUN 均跳过运行）。
        tc.configure_args.append("ac_cv_prog_cc_works=yes")
        tc.generate()

    def build(self):
        # ── Fix 0: Repair new-file patch format before applying ──
        # refresh-patch generates `--- a/filename` for new files, but
        # Conan's patch_ng requires `--- /dev/null`. Fix in-place:
        # if the "a/" target does not exist in the unpacked source tree,
        # it is a new-file patch -> rewrite its header to `--- /dev/null`.
        # Conan 2 中补丁从 export_sources_folder 读取（cache 构建时
        # exports_sources 复制到那里），本地/探索则可能在 source_folder。
        for base in (getattr(self, "export_sources_folder", "") or "",
                     self.source_folder):
            if not base:
                continue
            patch_dir = os.path.join(base, "patches")
            if not os.path.isdir(patch_dir):
                continue
            for name in sorted(os.listdir(patch_dir)):
                if not name.endswith(".patch"):
                    continue
                patch_path = os.path.join(patch_dir, name)
                content = load(self, patch_path)
                if content.startswith("--- a/") and "\n+++ b/" in content:
                    # "--- a/" 是 6 个字符，[6:] 取出相对路径（不带前导 /）
                    target = content.split("\n", 1)[0][6:]
                    if not os.path.exists(os.path.join(self.source_folder, target)):
                        content = content.replace("--- a/" + target,
                                                  "--- /dev/null", 1)
                        save(self, patch_path, content)
        apply_conandata_patches(self)

        # ── Fix 1: Patch ALL generated env scripts for local dev ──
        # The CI profile (ohos-aarch64) sets CONFIG_SHELL/SHELL/CC/CXX to
        # /data/service/hnp/bin/* which only exist on CI release workers.
        # Conan generates multiple .sh scripts (conanautotoolstoolchain.sh,
        # conanbuildenv-*.sh, etc.) that are sourced in sequence by
        # conanbuild.sh. We must patch every .sh in the generators folder
        # because the [buildenv] vars in conanbuildenv-*.sh are sourced
        # AFTER and override values set in earlier scripts.
        if not os.path.exists("/data/service/hnp/bin/bash"):
            bash_path = shutil.which("bash") or "bash"
            clang_path = shutil.which("clang") or "clang"
            clangxx_path = shutil.which("clang++") or "clang++"
            gen_folder = self.generators_folder
            if gen_folder and os.path.isdir(gen_folder):
                for name in os.listdir(gen_folder):
                    if not name.endswith(".sh"):
                        continue
                    script_path = os.path.join(gen_folder, name)
                    if not os.path.isfile(script_path):
                        continue
                    content = load(self, script_path)
                    if "/data/service/hnp/bin/" in content:
                        content = content.replace(
                            "/data/service/hnp/bin/bash", bash_path)
                        content = content.replace(
                            "/data/service/hnp/bin/clang++", clangxx_path)
                        content = content.replace(
                            "/data/service/hnp/bin/clang", clang_path)
                        save(self, script_path, content)

        # ── Fix 2: Patch configure to relax umask for HMFS ──
        # autoconf's config.status uses `umask 077` to create a secure temp
        # directory. On HMDFS (HarmonyOS), directories inherit a setgid bit
        # from their parent. With umask 077, the group loses execute (x)
        # permission, making the setgid bit uppercase 'S' (setgid without
        # execute). HMDFS then denies file creation in that directory even
        # for the owner. Changing to umask 022 preserves group execute,
        # keeping the setgid bit lowercase 's' and allowing writes.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            content = load(self, configure_path)
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                save(self, configure_path, content)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["speex"]
