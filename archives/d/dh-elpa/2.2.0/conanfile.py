#!/usr/bin/env python3
"""Conan recipe for dh-elpa 2.2.0 (OHOS aarch64).

dh-elpa is a debhelper addon that installs Emacs Lisp (ELPA-style) packages
into Debian package build directories, byte-compiling them via `emacs -batch`.
Pure Perl tools — dh_elpa/dh_elpa_test scripts + elpa.pm sequence addon; no C
compile step (build() only regenerates the man pages via pod2man).

Platform adaptations:
  - 0001-ohos-templatedir-env-override.patch: the debhelper template dir is
    hardcoded to /usr/share/debhelper/dh_elpa/emacsen-common upstream; the
    conan package layout has no /usr root, so the patch honors an optional
    DH_ELPA_TEMPLATEDIR env override (default keeps Debian behaviour).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches
from conan.tools.layout import basic_layout


class DhElpaConan(ConanFile):
    name = "dh-elpa"
    version = "2.2.0"
    description = ("dh-elpa — debhelper addon for Emacs Lisp (ELPA) packages "
                   "(pure Perl tools, no compile)")
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/emacsen-team/dh-elpa"
    url = ""  # CI fills this
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Runtime deps of the installed Perl tools (upstream Debian Depends
        # mapped to published ohpcd packages):
        #   debhelper              -> Debian::Debhelper::Dh_Lib (dh_elpa/elpa.pm)
        #   dpkg                   -> Dpkg::Version + dpkg-parsechangelog
        #   perl-config-tiny       -> Config::Tiny (elpa.pm / dh_elpa_test)
        #   emacs                  -> byte compilation + package installation
        #                            (dh_elpa's installer IS `emacs -batch`)
        # Module::Metadata (elpa.pm) 是 perl 核心双寿命模块（5.13.9 起随
        # perl core 分发）——由系统 perl 提供，无需 conan 依赖（制品仓
        # 检索 perl-module-metadata/* 为空，不得谎报依赖）。
        self.requires("debhelper/13.3.4")
        self.requires("dpkg/1.23.7")
        self.requires("perl-config-tiny/2.30")
        self.requires("emacs/29.1")
        # 依赖图冲突消解（CI 实测 Version conflict: ncurses/6.5 vs 6.4，
        # 冲突源自 emacs/29.1）: emacs 固定 ncurses/6.5，dpkg/1.23.7 固定
        # ncurses/6.4——consumer 用 override=True 统一到 6.5（仓库标准
        # 模式，100+ 先例）。代价: CI 需以 ncurses/6.5 重编 dpkg
        # （dpkg 的 ncurses 仅用于 update-alternatives 界面，配方已
        # --without-dselect，无实质影响）。
        self.requires("ncurses/6.5", override=True)

    def source(self):
        # 沙箱 get() 有 PermissionError 风险——download + 手动解压
        # （--no-same-owner 容忍所有权错误；cp -a 收拢含隐藏文件）
        download(self, self.conan_data["sources"]["url"],
                 "dh-elpa_2.2.0.tar.xz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xJf dh-elpa_2.2.0.tar.xz --no-same-owner || true")
        self.run("cp -a work/. . && rm -rf work")
        apply_conandata_patches(self)

    def build(self):
        # 上游 debian/rules: pod2man 生成 dh_elpa.1 + dh_elpa_test.1。
        # pod2man 在 OHOS worker 位于 /data/service/hnp/bin/pod2man；缺失时
        # 优雅跳过（非致命，如实 warning）。
        pod2man = "/data/service/hnp/bin/pod2man"
        if not os.path.isfile(pod2man):
            pod2man = shutil.which("pod2man")
        if pod2man:
            # CI 实测（build #51082）：本 fork conan 的 build() 默认 cwd 是
            # build-release 子目录（无源文件）——pod2man "Can't open dh_elpa"。
            # 显式 cwd=self.source_folder 并把 .1 生成在源目录，
            # package() 从 self.source_folder 取文件（in-source 布局，
            # dpkg 配方同款惯例）。
            for name in ("dh_elpa", "dh_elpa_test"):
                self.run(
                    f"{pod2man} -c Debhelper --section=1 {name} > {name}.1",
                    cwd=self.source_folder)
        else:
            self.output.warning("pod2man not found — man pages skipped")

    def package(self):
        # 挑文件安装（禁止整目录拷贝），与 Debian dh-elpa/dh-elpa-helper
        # 二进制包安装布局一致：
        #   bin/dh_elpa, bin/dh_elpa_test                           (0755)
        #   share/perl5/Debian/Debhelper/Sequence/elpa.pm  (dh sequence 插件)
        #   share/debhelper/dh_elpa/emacsen-common/{compat,install,remove}
        #   share/debhelper/autoscripts/prerm-elpa
        #   lib/dh-elpa/{install,remove}  (dh-elpa-helper 并入本包, 0755)
        #   share/emacs/site-lisp/elpa/dh-elpa.el
        #   share/man/man1/dh_elpa.1 + dh_elpa_test.1               (pod2man)
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for script in ("dh_elpa", "dh_elpa_test"):
            shutil.copy(os.path.join(self.source_folder, script),
                        os.path.join(bin_dir, script))
            os.chmod(os.path.join(bin_dir, script), 0o755)

        seq = os.path.join(self.package_folder, "share", "perl5",
                           "Debian", "Debhelper", "Sequence")
        os.makedirs(seq, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "elpa.pm"),
                    os.path.join(seq, "elpa.pm"))

        templ = os.path.join(self.package_folder, "share", "debhelper",
                             "dh_elpa", "emacsen-common")
        os.makedirs(templ, exist_ok=True)
        for name in ("compat", "install", "remove"):
            shutil.copy(os.path.join(self.source_folder,
                                     "emacsen-common", name),
                        os.path.join(templ, name))

        autoscripts = os.path.join(self.package_folder, "share", "debhelper",
                                   "autoscripts")
        os.makedirs(autoscripts, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "autoscripts",
                                 "prerm-elpa"),
                    os.path.join(autoscripts, "prerm-elpa"))

        helper = os.path.join(self.package_folder, "lib", "dh-elpa")
        os.makedirs(helper, exist_ok=True)
        for name in ("install", "remove"):
            shutil.copy(os.path.join(self.source_folder, "helper", name),
                        os.path.join(helper, name))
            os.chmod(os.path.join(helper, name), 0o755)

        elpa_dir = os.path.join(self.package_folder, "share", "emacs",
                                "site-lisp", "elpa")
        os.makedirs(elpa_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "dh-elpa.el"),
                    os.path.join(elpa_dir, "dh-elpa.el"))

        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        for name in ("dh_elpa.1", "dh_elpa_test.1"):
            src = os.path.join(self.source_folder, name)
            if os.path.isfile(src):
                os.makedirs(man_dir, exist_ok=True)
                shutil.copy(src, os.path.join(man_dir, name))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
