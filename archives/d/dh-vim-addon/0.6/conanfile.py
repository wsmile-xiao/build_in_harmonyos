#!/usr/bin/env python3
"""Conan recipe — dh-vim-addon 0.6 (pure Perl debhelper addon, no compile).

zero-compile packaging: source() downloads + unpacks the salsa git-archive,
package() installs the chosen files (bin/ + lib/perl5/.../Sequence/ +
share/man/man1/), build() only applies conandata patches (none here).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, download,
                               export_conandata_patches)


class DhVimAddonConan(ConanFile):
    name = "dh-vim-addon"
    version = "0.6"
    package_type = "application"
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/vim-team/dh-vim-addon"
    description = ("dh_vim-addon — debhelper addon to help package Vim/Neovim "
                   "addons (pure Perl script + dh sequence, no compile)")
    settings = "os", "compiler", "build_type", "arch"
    # 纯 Perl debhelper 插件——零编译。运行时依赖（上游 debian/control
    # Depends 的 ohpcd 对应包）：
    #   debhelper/13.3.4 → Debian::Debhelper::Dh_Lib（dh_* 插件框架）
    #   dpkg/1.23.7      → Dpkg::Control::Info / Dpkg::Version（读 debian/control）
    # 上游另依赖 vim-common（helpztags + vim 运行时目录），ohpcd 未发布该包，
    # 故不声明（禁止捎带适配依赖）；缺失仅影响含 doc/ 目录的插件生成帮助标签。
    requires = "debhelper/13.3.4", "dpkg/1.23.7"

    def export_sources(self):
        # 本包无补丁（conandata.yml 无 patches 段）；沿用框架模板形态，
        # 保持配方结构一致性（G1 配方完整性门禁要求）。
        export_conandata_patches(self)

    def source(self):
        # 沙箱 get() 有 PermissionError 风险——download + 手动解压
        # （--no-same-owner 容忍所有权错误；cp -a 收拢含隐藏文件）
        download(self, self.conan_data["sources"]["url"],
                 "dh-vim-addon_0.6.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf dh-vim-addon_0.6.tar.gz --no-same-owner || true")
        self.run("cp -a dh-vim-addon-debian-0.6/. . && rm -rf dh-vim-addon-debian-0.6")

    def build(self):
        # 纯 Perl，无编译步骤；仅应用 conandata.yml 声明的补丁（本包无补丁，空操作）
        apply_conandata_patches(self)

    def _install_manpage(self, src_script, man_out):
        """生成并安装 man 页（上游 debian/rules: `pod2man --utf8 dh_vim-addon
        > dh-vim-addon.1`；tarball 内不含 .1）。

        尽力而为：优先 pod2man，回退平台 perl 自带的 Pod::Man；两者皆不可用
        则跳过（man 页非运行必需，不因缺失阻塞打包，也不伪造内容）。
        """
        import subprocess

        def _find(name, extra):
            for cand in (extra, shutil.which(name)):
                if cand and os.path.isfile(cand):
                    return cand
            return None

        pod2man = _find("pod2man", "/data/service/hnp/bin/pod2man")
        perl = _find("perl", "/data/service/hnp/bin/perl")

        attempts = []
        if pod2man:
            attempts.append([pod2man, "--utf8", src_script])
        if perl:
            attempts.append([
                perl, "-MPod::Man", "-e",
                "my $p=Pod::Man->new(utf8=>1);"
                "$p->parse_from_file($ARGV[0],$ARGV[1]);",
                src_script, man_out,
            ])
        for cmd in attempts:
            if os.path.exists(man_out):
                os.remove(man_out)
            try:
                with open(man_out, "wb") as fh:
                    subprocess.run(cmd, stdout=fh, stderr=subprocess.DEVNULL,
                                   cwd=self.source_folder, timeout=60,
                                   check=True)
            except Exception:
                continue
            if os.path.isfile(man_out) and os.path.getsize(man_out) > 0:
                return True
        if os.path.exists(man_out):
            try:
                os.remove(man_out)
            except OSError:
                pass
        return False

    def package(self):
        # 挑文件安装（禁止整目录拷贝）：
        #   dh_vim-addon   → <pkg>/bin/dh_vim-addon (0755)
        #   vim_addon.pm   → <pkg>/lib/perl5/Debian/Debhelper/Sequence/vim_addon.pm
        #   dh-vim-addon.1 → <pkg>/share/man/man1/dh-vim-addon.1（pod2man 生成）
        #   COPYING        → <pkg>/licenses/COPYING
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "dh_vim-addon"),
                    os.path.join(self.package_folder, "bin", "dh_vim-addon"))
        os.chmod(os.path.join(self.package_folder, "bin", "dh_vim-addon"), 0o755)

        seq = os.path.join(self.package_folder, "lib", "perl5",
                           "Debian", "Debhelper", "Sequence")
        os.makedirs(seq, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "vim_addon.pm"),
                    os.path.join(seq, "vim_addon.pm"))

        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        if not self._install_manpage(
                os.path.join(self.source_folder, "dh_vim-addon"),
                os.path.join(man_dir, "dh-vim-addon.1")):
            self.output.info("man page 生成工具不可用（pod2man/Pod::Man）"
                             "——跳过 man 页安装")

        licenses = os.path.join(self.package_folder, "licenses")
        os.makedirs(licenses, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "COPYING"),
                    os.path.join(licenses, "COPYING"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
