#!/usr/bin/env python3
"""Conan recipe — consolation 0.0.10 (autotools, application, OHOS PC).

consolation is a daemon that provides GPM-like copy-paste/scrolling for the
Linux **virtual console**: it reads pointer events through libinput (which
brings libevdev + libudev) and writes selections back to the VT.  Installed
artifact is a single daemon binary (`sbin/consolation`) — hence
`package_type = "application"`.

构建要点:
- 依赖全部经 pkg-config 解析(configure.ac: PKG_CHECK_MODULES 对
  libinput/libudev/libevdev),由 conan 依赖图 + PkgConfigDeps 供给;
- 上游 man 页(consolation.8)由**运行编译产物**生成
  (src/Makefile.am 内联规则执行 ./consolation),交叉构建下不可行,
  按「文档不构建」口径在构建前中性化 src/Makefile.in 的
  dist_man_MANS(与其它包 -Ddocumentation=false / --disable-manpages
  同口径,见 notes.md);
- 1 个 portability 补丁:musl 无 glibc 全局
  program_invocation_short_name(见 conandata.yml)。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ConsolationConan(ConanFile):
    name = "consolation"
    version = "0.0.10"
    description = ("Copy-paste and scrolling daemon for the Linux virtual "
                   "console (libinput based)")
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/consolation-team/consolation"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # configure.ac 依赖:libinput(>=1.5)、libudev、libevdev(>=0.4)。
        # libinput/1.26.2 是 main 上已构建发布的组合成员,其自身依赖
        # libevdev/1.13.7、mtdev/1.1.7、eudev/3.2.14(libudev 提供方,
        # pkg_config_name=libudev),且三者均以 transitive_* 声明——
        # 因此这里单条 requires 即可让 libinput.pc / libudev.pc /
        # libevdev.pc / mtdev.pc 全部出现在本包的 PkgConfigDeps 输出里。
        # 显式 transitive_headers/libs:consolation 直接 include 这些
        # 库的头并链接它们。
        self.requires("libinput/1.26.2", transitive_headers=True,
                      transitive_libs=True)

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"],
            sha256=source_data.get("sha256", ""), strip_root=True)

    def export_sources(self):
        # patches/ 必须显式导出，否则 apply_conandata_patches 找不到文件
        export_conandata_patches(self)

    def validate(self):
        # consolation 是 Linux VT 输入栈组件(evdev + udev + epoll)。
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"consolation requires a Linux-kernel VT/input stack, "
                f"not {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        self._ensure_tmpdir()
        # configure.ac 走 PKG_CHECK_MODULES → 需要依赖图的 .pc
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        self._neutralize_man_rule()
        self._fix_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        # 小包,单线程构建足够且日志可读
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 唯一产物是守护进程 sbin/consolation(sbin_PROGRAMS)
        self.cpp_info.bindirs = ["sbin"]

    # ── Helper methods ──────────────────────────────────────────

    def _ensure_tmpdir(self):
        # HarmonyOS 的 /tmp 是只读 erofs(E002)— 指到可写目录
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _fix_configure_umask(self):
        """HMDFS 上 configure 内 `umask 077 && mktemp -d` 会产出权限异常的临时
        文件,config.status 的临时文件机制随之失效(实测报
        "could not setup config files machinery")。与 eudev 3.2.14 配方的
        umask 077→022 修法一致,在 configure 里做文本替换(零补丁)。
        """
        pattern = "umask 077"
        for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"),
                             recursive=True):
            try:
                with open(cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if pattern in text:
                with open(cfg, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text.replace(pattern, "umask 022"))
                self.output.info(
                    f"relaxed umask 077 -> 022 in {os.path.relpath(cfg, self.source_folder)}")

    def _neutralize_man_rule(self):
        """Neutralise the cross-build-hostile man page rule before configure.

        Upstream generates `consolation.8` by **executing the just-built
        daemon** (src/Makefile.in: `./consolation | sed ... > consolation.8`),
        wired into `all-am: ... $(MANS)`.  A cross-built aarch64 binary
        cannot run on the build host, so `make` would fail.  The package has
        no configure switch for docs, so — same policy as the repo's
        `-Ddocumentation=false` / `--disable-manpages` on other packages —
        blank `dist_man_MANS` in the template.  configure then propagates
        the empty MANS into the generated Makefile and `install-man` becomes
        a no-op.
        """
        pattern = "dist_man_MANS = "
        for mf in glob.glob(os.path.join(self.source_folder, "src", "Makefile.in")):
            try:
                with open(mf, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except OSError:
                continue
            hit = False
            with open(mf, "w", encoding="utf-8", newline="\n") as f:
                for line in lines:
                    if line.startswith(pattern):
                        f.write(pattern + "\n")
                        hit = True
                    else:
                        f.write(line)
            if hit:
                self.output.info(
                    "neutralised upstream man rule in src/Makefile.in "
                    "(cross build cannot run the daemon to render the page)")
