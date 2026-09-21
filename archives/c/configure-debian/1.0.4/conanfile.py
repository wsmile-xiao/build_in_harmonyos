import os

from conan import ConanFile
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout

# 上游 Locale::gettext 是 XS 模块（DynaLoader bootstrap），构建需 libintl.h
# ——OHOS musl 无此头文件（Makefile.PL conftest 实测失败："gettext function
# not found. Please install libintl"；gettext 的 C 符号 musl libc 自带，卡点
# 仅在头文件）——且本包不带 .mo catalog，C 区域恒等语义（gettext($m)==$m）
# 即正确行为。vendored 最小纯 Perl shim（同名 namespace），让主脚本的
# `use Locale::gettext;` + 裸调 gettext() 可编译可运行（实测：perl -c
# syntax OK + 非 root 实跑过编译到 root 门禁）。
GETTEXT_SHIM = """\
package Locale::gettext;

# OHOS pure-Perl shim for Locale::gettext 1.07 (see recipe comments).
use strict;
use warnings;
require Exporter;
our @ISA = qw(Exporter);
our @EXPORT = qw(gettext dgettext dcgettext ngettext dngettext
                 textdomain bindtextdomain bind_textdomain_codeset);
our $VERSION = "1.07-ohos-shim";

sub gettext { my ($m) = @_; return defined($m) ? $m : ""; }
sub dgettext { my ($d, $m) = @_; return defined($m) ? $m : ""; }
sub dcgettext { my ($d, $m, $c) = @_; return defined($m) ? $m : ""; }
sub ngettext { my ($s, $p, $n) = @_; return ($n == 1) ? $s : $p; }
sub dngettext { my ($d, $s, $p, $n) = @_; return ($n == 1) ? $s : $p; }
sub textdomain { return 1; }
sub bindtextdomain { return ""; }
sub bind_textdomain_codeset { return ""; }
1;
"""


class ConfigureDebianConan(ConanFile):
    name = "configure-debian"
    version = "1.0.4"
    description = ("configure-debian - central configuration program for "
                   "packages using debconf (pure perl script)")
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/debian/configure-debian"
    url = ""
    package_type = "application"
    exports_sources = "conandata.yml"

    settings = "os", "compiler", "build_type", "arch"

    # 无 conan requires：脚本编译期唯一依赖 Locale::gettext 由本包 vendored
    # shim 满足（自包含）；root 交互路径的外部命令 dpkg-reconfigure（属
    # debconf 包）/ apt-cache（apt 包）/ tempfile（miscfiles 包）均为 Debian
    # 用户态工具，本归档环境无对应配方 —— 按 acme.sh 先例如实声明边界，
    # 不硬拉无关依赖

    def layout(self):
        basic_layout(self)

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "configure-debian_1.0.4.tar.xz",
                 sha256=self.conan_data["sources"]["sha256"])
        # get() 在 CI 沙箱 PermissionError（dpkg 先例）——手动解压
        self.run("tar -xJf configure-debian_1.0.4.tar.xz --no-same-owner || true")
        self.run("cp -a configure-debian-1.0.4/. . && rm -rf configure-debian-1.0.4")

    def build(self):
        # 纯脚本包：上游 Makefile 仅 install（无编译段）
        pass

    def package(self):
        # 主脚本 → bin/（上游 Makefile 装 sbin，按归档惯例映射 bin/）
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "configure-debian", src=self.source_folder,
             dst=bindir, keep_path=False)
        main_script = os.path.join(bindir, "configure-debian")
        # shebang 适配：OHOS 无 /usr/bin/perl（perl 由 hnp 提供
        # /data/service/hnp/bin/perl）——house perl shebang 先例
        with open(main_script, "r", encoding="utf-8", newline="\n") as f:
            content = f.read()
        content = content.replace("#!/usr/bin/perl -w",
                                  "#!/usr/bin/env perl -w", 1)
        with open(main_script, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.chmod(main_script, 0o755)

        # debconf helper → share/configure-debian/
        helper_dir = os.path.join(self.package_folder, "share",
                                  "configure-debian")
        os.makedirs(helper_dir, exist_ok=True)
        copy(self, "configure-debian-debconf", src=self.source_folder,
             dst=helper_dir, keep_path=False)
        os.chmod(os.path.join(helper_dir, "configure-debian-debconf"), 0o755)

        # 图标 + 菜单 → share/pixmaps/ + share/applications/
        pixmaps = os.path.join(self.package_folder, "share", "pixmaps")
        os.makedirs(pixmaps, exist_ok=True)
        copy(self, "configure-debian.xpm", src=self.source_folder,
             dst=pixmaps, keep_path=False)
        copy(self, "configure-debian-48x48.png", src=self.source_folder,
             dst=pixmaps, keep_path=False)
        applications = os.path.join(self.package_folder, "share",
                                    "applications")
        os.makedirs(applications, exist_ok=True)
        copy(self, "configure-debian.desktop", src=self.source_folder,
             dst=applications, keep_path=False)

        # vendored Locale/gettext.pm → lib/perl5/（runenv PERL5LIB 暴露）
        perl_dir = os.path.join(self.package_folder, "lib", "perl5", "Locale")
        os.makedirs(perl_dir, exist_ok=True)
        with open(os.path.join(perl_dir, "gettext.pm"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(GETTEXT_SHIM)

        copy(self, "debian/copyright", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.runenv.define(
            "PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
