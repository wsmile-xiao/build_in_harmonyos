import os

from conan import ConanFile
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout


class ConsoleCommonConan(ConanFile):
    name = "console-common"
    version = "0.7.92"
    description = ("console-common - basic infrastructure for text console "
                   "setup (install-keymap(8) + dh-consoledata + keymap "
                   "declaration scripts, pure shell/perl)")
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/console-common"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # 运行期外部命令消费关系（install-keymap/kbd-config/config.in 脚本
        # system()/backtick 全文核对，勿凭命令名前缀猜包）：
        #   install-keymap → loadkeys/fgconsole/dumpkeys（kbd 包）、
        #     tempfile（debianutils 包）、dpkg --print-architecture（dpkg 包）
        #   config.in → dpkg --compare-versions（dpkg 包）
        # gzip/awk/diff/md5sum 由 OHOS 基础系统（toybox/busybox）提供，不声明
        self.requires("kbd/2.9.0")
        self.requires("debianutils/5.23.2")
        self.requires("dpkg/1.23.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "console-common_0.7.92.tar.xz",
                 sha256=self.conan_data["sources"]["sha256"])
        # get() 在 CI 沙箱 PermissionError（dpkg 先例）——手动解压
        self.run("tar -xJf console-common_0.7.92.tar.xz --no-same-owner || true")
        self.run("cp -a console-common-0.7.92/. . && rm -rf console-common-0.7.92")

    def build(self):
        # 上游 Makefile 无编译段（纯 install + 两处 sed 模板展开）；等价
        # 生成放 package()（避免 dpkg-parsechangelog 依赖，版本直接取 conanfile）
        pass

    @property
    def _dhdir(self):
        return "/usr/share/debhelper/dh-consoledata"

    @property
    def _kmapdir(self):
        return "/usr/share/console/lists/keymaps"

    @property
    def _lcddep(self):
        return f"console-common (>= {self.version})"

    def _fix_shebang(self, path):
        # shebang 适配：OHOS 无 /usr/bin/perl（perl 由 hnp 提供
        # /data/service/hnp/bin/perl）——house perl shebang 先例
        with open(path, "r", encoding="utf-8", newline="\n") as f:
            content = f.read()
        content = content.replace("#!/usr/bin/perl -w",
                                  "#!/usr/bin/env perl -w", 1)
        content = content.replace("#!/usr/bin/perl\n",
                                  "#!/usr/bin/env perl\n", 1)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.chmod(path, 0o755)

    def package(self):
        pf = self.package_folder
        bindir = os.path.join(pf, "bin")
        consoledir = os.path.join(pf, "share", "console")
        dhdata = os.path.join(pf, "share", "debhelper", "dh-consoledata")
        autoscripts = os.path.join(pf, "share", "debhelper", "autoscripts")
        for d in (bindir, consoledir, dhdata, autoscripts):
            os.makedirs(d, exist_ok=True)

        # install-keymap：上游 sbin → house bin/（0755）；#!/bin/sh 保留
        # （OHOS 有 /bin/sh）
        copy(self, "install-keymap", src=self.source_folder, dst=bindir,
             keep_path=False)
        os.chmod(os.path.join(bindir, "install-keymap"), 0o755)

        # kbd-config：上游 bin（0755，#!/bin/sh 保留）
        copy(self, "kbd-config", src=self.source_folder, dst=bindir,
             keep_path=False)
        os.chmod(os.path.join(bindir, "kbd-config"), 0o755)

        # dh_consoledata：dh_consoledata.in → @DHDIR@/@KMAPDIR@/@LCDDEP@
        # 替换 → bin/。等价上游 Makefile 的
        # sed -e "s^@DHDIR@^${dhdatadir}^" -e "s^@KMAPDIR@^${kmapdatadir}^"
        # -e "s^@LCDDEP@^${lcddep}^"；lcddep 的版本号上游经
        # dpkg-parsechangelog 取（Debian 构建工具链，OHOS 无配方），
        # 此处直接取 conanfile version
        with open(os.path.join(self.source_folder, "dh_consoledata.in"),
                  "r", encoding="utf-8", newline="\n") as f:
            dh = f.read()
        dh = dh.replace("@DHDIR@", self._dhdir)
        dh = dh.replace("@KMAPDIR@", self._kmapdir)
        dh = dh.replace("@LCDDEP@", self._lcddep)
        dh_path = os.path.join(bindir, "dh_consoledata")
        with open(dh_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(dh)
        self._fix_shebang(dh_path)

        # getkmapchoice.pl：在 #####COMMON##### 标记行后插入 common.pl
        # （等价上游 sed '/^#####COMMON####$/ r common.pl'，标记行保留）
        with open(os.path.join(self.source_folder, "common.pl"),
                  "r", encoding="utf-8", newline="\n") as f:
            common = f.read()
        with open(os.path.join(self.source_folder, "getkmapchoice.pl.in"),
                  "r", encoding="utf-8", newline="\n") as f:
            gk_lines = f.read().split("\n")
        out = []
        for line in gk_lines:
            out.append(line)
            if line.strip() == "#####COMMON#####":
                out.append(common.rstrip("\n"))
        gk_path = os.path.join(consoledir, "getkmapchoice.pl")
        with open(gk_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(out))
        self._fix_shebang(gk_path)

        # ps2-to-riscpc：awk 脚本 → share/console/（0755，
        # shebang #! /usr/bin/awk -f → env）
        copy(self, "ps2-to-riscpc", src=self.source_folder, dst=consoledir,
             keep_path=False)
        ps2 = os.path.join(consoledir, "ps2-to-riscpc")
        with open(ps2, "r", encoding="utf-8", newline="\n") as f:
            c = f.read()
        c = c.replace("#! /usr/bin/awk -f", "#!/usr/bin/env awk -f", 1)
        with open(ps2, "w", encoding="utf-8", newline="\n") as f:
            f.write(c)
        os.chmod(ps2, 0o755)

        # dh-consoledata 数据文件：common.pl + config.in（上游 0644，
        # debian/rules override_dh_fixperms 显式 chmod +x → 0755）
        copy(self, "common.pl", src=self.source_folder, dst=dhdata,
             keep_path=False)
        copy(self, "config.in", src=self.source_folder, dst=dhdata,
             keep_path=False)
        self._fix_shebang(os.path.join(dhdata, "config.in"))

        # templates（po2debconf 生成）不生成：po-debconf 是 Debian 构建工具
        # （OHOS 无配方），且 keymap debconf 问题模板的消费方是 console-data
        # 键图包（未归档）——环境边界，notes.md 记录

        # postinst-lcd-keymaps autoscript（上游 0644）
        copy(self, "postinst-lcd-keymaps", src=self.source_folder,
             dst=autoscripts, keep_path=False)

        copy(self, "debian/copyright", src=self.source_folder,
             dst=os.path.join(pf, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
