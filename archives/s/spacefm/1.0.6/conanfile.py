#!/usr/bin/env python3
"""Conan recipe — spacefm 1.0.6 (autotools, GTK2 桌面文件管理器).

任务卡 #10827（2404_87638649）。OHOS 适配策略：
- autotools 构建（tarball 自带 configure，免 autoreconf）
- 三元组补丁 0001：config.guess 加 HarmonyOS 分支（aarch64-unknown-linux-ohos）、
  config.sub 认 linux-ohos*（vlc 3.0.23 同款范式）
- udev 依赖：configure.ac 无 --disable-udev 开关（HAL 关闭时无条件
  PKG_CHECK_MODULES(libudev)），走 eudev/3.2.14 制品仓（libudev.pc）
- intltool：configure 内嵌 AC_PROG_INTLTOOL 探测 + data/Makefile.am 的
  @INTLTOOL_DESKTOP_RULE@——系统无 intltool/perl 栈，按 activity-log 0.9.7
  先例写 shim 脚本（--version 应答+其余 no-op），并 --disable-nls 裁剪 po 层
- 裁剪：video-thumbnails（ffmpegthumbnailer 不在制品仓）、
  startup-notification（OHOS 无桌面启动通知栈）
- HMDFS umask 陷阱（vlc 先例）：configure 内嵌 `umask 077` 创建的临时目录
  在 HMDFS 不可写，构建前 sed 替换为 umask 022

上游测试：无自动化测试套件（tarball 无 test/ 目录、Makefile.am 无 TESTS）。
test_package 消费者侧冒烟：--version / --help / AArch64 ELF 三断言。
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpacefmConan(ConanFile):
    name = "spacefm"
    version = "1.0.6"
    description = "SpaceFM: multi-panel tabbed GTK2 file and desktop manager"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/IgnorantGuru/spacefm"
    url = "https://github.com/IgnorantGuru/spacefm"
    topics = ("file-manager", "gtk2", "desktop", "fileman")

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"
    # PkgConfigDeps: 为 gtk2/eudev requires 生成 .pc（configure 的
    # PKG_CHECK_MODULES(GTK...) 探测需要）；VirtualBuildEnv 导出
    # PKG_CONFIG_PATH 指向生成的 .pc（vlc 3.0.23 同款，create5 实证缺此必挂）
    generators = "PkgConfigDeps", "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        # configure.ac: HAL off -> PKG_CHECK_MODULES(LIBUDEV, libudev >= 143)
        # 无 --disable-udev 开关，走 eudev（libudev.pc 提供方）
        self.requires("eudev/3.2.14")
        self.requires("gtk2/2.24.33")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("spacefm is prepared for Linux/OHOS targets only")

    def generate(self):
        # HMDFS umask 陷阱：configure 内嵌 umask 077（vlc 3.0.23 先例）
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            replace_in_file(self, cfg, "umask 077", "umask 022")
            # The bundled intltool.m4 unconditionally probes
            # `$PERL -e "require XML::Parser"`; the real perl (5.42) lacks
            # that module. Neutralize by requiring a core module instead —
            # belt-and-suspenders with the perl shim (activity-log 0.9.7
            # precedent covers the shim side only).
            replace_in_file(self, cfg, "require XML::Parser", "require strict")

        shims = self._write_intltool_shims()
        self._shim_dir = shims
        # conanbuild aggregated env — actually applied to configure/make
        # subprocesses (a custom save_script env is NOT auto-sourced;
        # create3/create4 evidenced PATH never reaching configure).
        self.buildenv_info.prepend_path("PATH", shims)

        tc = AutotoolsToolchain(self)
        # Legacy tentative definitions: vfs-file-info.c / vfs-dir.c both
        # define xsets / evt_win_* at file scope (pre-C99 common-symbol
        # style). clang 15 defaults to -fno-common -> duplicate-symbol link
        # errors (create8). -fcommon restores the legacy merge semantics.
        tc.cflags.append("-fcommon")
        tc.configure_args.extend([
            "--disable-nls",
            "--disable-video-thumbnails",
            "--disable-startup-notification",
        ])
        tc.generate()

    def _write_intltool_shims(self):
        """intltool/gettext 探测 shim（activity-log 0.9.7 先例）：
        configure 的 AC_PROG_INTLTOOL 与 gettext 宏即使 --disable-nls 也
        探测工具版本；data/Makefile.am 的 INTLTOOL_DESKTOP_RULE 在 make
        时调 intltool-merge。shim 只应答 --version，其余 no-op。"""
        shim_dir = os.path.join(self.build_folder, "ohos-build-tools")
        Path(shim_dir).mkdir(parents=True, exist_ok=True)
        scripts = {
            "intltool-update": (
                "#!/bin/sh\ncase \"$1\" in\n"
                "  --version) echo 'intltool-update (intltool) 0.51.0' ;;\n"
                "esac\n"
            ),
            "intltool-merge": (
                # no-op merge: copy input (2nd-to-last arg) to output (last
                # arg) so make targets materialize untranslated
                "#!/bin/sh\n"
                "prev=\"\"\nlast=\"\"\n"
                "for a in \"$@\"; do prev=\"$last\"; last=\"$a\"; done\n"
                "if [ -n \"$last\" ] && [ -n \"$prev\" ] && [ -f \"$prev\" ]; then\n"
                "  cp \"$prev\" \"$last\"\nfi\nexit 0\n"
            ),
            "intltool-extract": "#!/bin/sh\nexit 0\n",
            "msgmerge": (
                "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'msgmerge (GNU gettext-tools) 0.22'\n  exit 0\nfi\nexit 1\n"
            ),
            "xgettext": (
                "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'xgettext (GNU gettext-tools) 0.22'\n  exit 0\nfi\nexit 0\n"
            ),
            "msgfmt": (
                "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'msgfmt (GNU gettext-tools) 0.22'\n  exit 0\nfi\nexit 0\n"
            ),
            # intltool.m4 unconditionally probes `perl -e "require XML::Parser"`;
            # the real perl (5.42) lacks that module. Intercept the probe,
            # delegate everything else to the real interpreter.
            "perl": (
                "#!/bin/sh\n"
                "for a in \"$@\"; do\n"
                "  case \"$a\" in *XML::Parser*) exit 0 ;; esac\n"
                "done\n"
                "exec /data/service/hnp/bin/perl \"$@\"\n"
            ),
        }
        for name, content in scripts.items():
            p = os.path.join(shim_dir, name)
            Path(p).write_text(content, encoding="utf-8")
            os.chmod(p, 0o755)
        return shim_dir

    def build(self):
        apply_conandata_patches(self)
        # Custom save_script env is NOT auto-applied to Autotools subshells
        # (create3 evidenced: configure resolved msgfmt/perl from
        # /data/service/hnp/bin without the shims). Prepend the shim dir to
        # the process PATH directly so configure/make subshells inherit it.
        shim_dir = getattr(self, "_shim_dir", "")
        if shim_dir and os.path.isdir(shim_dir):
            os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")
        # Legacy tentative definitions (xsets/evt_* defined at file scope in
        # multiple .c files): clang 15 defaults to -fno-common -> duplicate
        # symbol link errors (create8/9). The env-script plumbing does not
        # reach the autotools subshells in this conan build (same root cause
        # as the PATH issue in create3/4), so inject CFLAGS into the process
        # environment — configure bakes it into the generated Makefile.
        os.environ["CFLAGS"] = (os.environ.get("CFLAGS", "") + " -fcommon").strip()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        # install-sh -c -d 并行竞态：make -j 并发 install 时两个 install-sh
        # 同时 mkdir bin/（HMDFS 上后到者 File exists 报错，create11 实证）。
        # 串行化 install 消除竞态。
        autotools.install(args=["-j1"])
        # bin/spacefm + share/pixmaps + share/applications 已由 make install 落位

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
