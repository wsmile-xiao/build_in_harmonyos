#!/usr/bin/env python3
"""Conan recipe — debarchiver 0.11.7（Debian 仓库管理工具，纯 Perl 脚本）。

debarchiver 收 `.changes` 包、建 apt 索引、可选 gpg 签名，是 Debian 存档仓库的
常用工具。上游为单个 Perl 脚本 `src/debarchiver.pl`（114 KB）+ 配置 + man 页。

OHOS 适配要点（均实测）：
1. **shebang**：上游 `#!/usr/bin/perl`，而 **OHOS 无 `/usr/bin/perl`**（perl 由
   ohpcd 的 perl 包提供，位于包内 `bin/`）→ 改为 `#!/usr/bin/env perl`，由 PATH 解析。
2. ★ **OHOS 无 coreutils `install`（E188）** —— 上游 `src/Makefile` 与
   `conf/Makefile` 均用 `install -m755` / `install -m644` 落盘，而 OHOS 上该命令
   **不存在**（实测 `command -v install` 为空）→ **不能调用 `make install`**，
   改由本配方按上游布局自行落盘。
3. **man 页**：上游 `po4a/Makefile` 依赖 `podselect`（**ohpcd 的 perl 包内无
   `Pod::Select`**）与 `po4a`（未适配），故无法走上游 po4a 流程；改用 perl 自带的
   `Pod::Man` 直接从 `debarchiver.pl` 内嵌 POD 生成 `debarchiver.1`。
   man 页属文档而非功能，生成失败**不影响**主程序可用性（会如实记录）。
4. **运行期目录硬编码**：`$inputdir`/`$destdir`/`$cachedir` 默认指向
   `/var/lib/debarchiver` 与 `/var/cache/debarchiver`；这些目录不存在时脚本会
   `chdir` 失败并以 `EXIT: 2` 退出。**已实测 `--configfile` 可覆盖它们**
   （见 test_package），故包本身无需改这些默认值。

R32: `settings.os` 判断用 `in ("Linux", "OHOS")`。
R33: 不依赖未定义的 shell 环境变量。
"""
import glob
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, get, mkdir, chmod
from conan.tools.layout import basic_layout

SCRIPT = os.path.join("src", "debarchiver.pl")


class DebarchiverConan(ConanFile):
    name = "debarchiver"
    version = "0.11.7"
    description = ("debarchiver — Debian repository archiver: collects uploaded "
                   ".changes packages, builds apt indexes and can sign releases")
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/debarchiver"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 硬前置：脚本内 `use OpaL::action / OpaL::read`（BEGIN 阶段即加载）
        self.requires("opalmod/0.2.2.1")
        # 运行期：shebang 为 `#!/usr/bin/env perl`，消费者需能解析到 perl
        self.requires("perl/5.42.2", transitive_headers=False, transitive_libs=False)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        script = os.path.join(self.source_folder, SCRIPT)
        if not os.path.isfile(script):
            raise ConanException(f"debarchiver: 未找到上游脚本 {SCRIPT}")

        # shebang：#!/usr/bin/perl → #!/usr/bin/env perl（OHOS 无 /usr/bin/perl）
        #
        # ⚠️ 必须按**二进制**改写，不能用 replace_in_file：
        #    上游 debarchiver.pl **不是 UTF-8**（实测为 Latin-1：offset 924 处
        #    0xe9 是作者名 "Valéry Perrin" 的 é），以 UTF-8 解码会抛
        #    UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9。
        #    二进制改写只动首行，不触碰其余字节，也不改变文件编码。
        with open(script, "rb") as fh:
            raw = fh.read()
        if not raw.startswith(b"#!"):
            raise ConanException("debarchiver: 脚本未以 shebang 开头，改写假设失效")
        first_line, sep, rest = raw.partition(b"\n")
        if b"perl" not in first_line:
            raise ConanException(
                f"debarchiver: shebang 非 perl，无法按预期改写: {first_line[:60]!r}")
        new_raw = b"#!/usr/bin/env perl" + sep + rest
        with open(script, "wb") as fh:
            fh.write(new_raw)

        # 自校：首行确已改写；且除首行外其余字节**逐字节未变**（证明未破坏文件）
        with open(script, "rb") as fh:
            check = fh.read()
        if check.split(b"\n", 1)[0] != b"#!/usr/bin/env perl":
            raise ConanException("debarchiver: shebang 改写未生效")
        if check.split(b"\n", 1)[1] != rest:
            raise ConanException(
                "debarchiver: 改写后首行以外的内容发生变化（不应发生）")
        self.output.info("debarchiver: shebang 已改写为 #!/usr/bin/env perl"
                         "（二进制改写，文件其余字节未变）")

    def build(self):
        # R32：平台判断须含 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"debarchiver: 不支持的 OS: {self.settings.os}")

        # 纯 Perl，无编译步骤。可选生成 man 页（Pod::Man 属 perl 自带模块）。
        man = os.path.join(self.build_folder, "debarchiver.1")
        script = os.path.join(self.source_folder, SCRIPT)
        try:
            self.run(
                f'perl -MPod::Man -e "Pod::Man->new(section=>1,center=>\'Debarchiver\')'
                f'->parse_from_file(\'{script}\', \\*STDOUT)" > "{man}"')
        except ConanException:
            self.output.warning("debarchiver: Pod::Man 不可用，跳过 man 页生成（不影响主程序）")
        if os.path.isfile(man) and os.path.getsize(man) == 0:
            os.remove(man)

    def package(self):
        # ⚠️ 不调 `make install`：E188——OHOS 无 coreutils install
        bindir = os.path.join(self.package_folder, "bin")
        etcdir = os.path.join(self.package_folder, "etc")
        man1 = os.path.join(self.package_folder, "share", "man", "man1")
        mkdir(self, bindir)
        mkdir(self, etcdir)
        mkdir(self, os.path.join(etcdir, "logcheck", "ignore.d.workstation"))

        # 主程序：上游 Makefile 装为 usr/bin/debarchiver（去掉 .pl 后缀）
        copy(self, "debarchiver.pl", src=os.path.join(self.source_folder, "src"),
             dst=bindir, keep_path=False)
        os.rename(os.path.join(bindir, "debarchiver.pl"),
                  os.path.join(bindir, "debarchiver"))
        chmod(self, os.path.join(bindir, "debarchiver"), execute=True)

        # 配置（上游 conf/Makefile 装到 /etc 与 /etc/logcheck/...）
        copy(self, "debarchiver.conf", src=os.path.join(self.source_folder, "conf"),
             dst=etcdir, keep_path=False)
        # ⚠️ 上游对 logcheck 文件**改了名**：源文件名 debarchiver.logcheck，
        #    安装后为 .../ignore.d.workstation/debarchiver（见 conf/Makefile:25）。
        #    故这里必须同步重命名，否则落盘名与上游布局不一致。
        copy(self, "debarchiver.logcheck", src=os.path.join(self.source_folder, "conf"),
             dst=os.path.join(etcdir, "logcheck", "ignore.d.workstation"),
             keep_path=False)
        os.rename(
            os.path.join(etcdir, "logcheck", "ignore.d.workstation", "debarchiver.logcheck"),
            os.path.join(etcdir, "logcheck", "ignore.d.workstation", "debarchiver"))

        # man 页（若已生成）
        man = os.path.join(self.build_folder, "debarchiver.1")
        if os.path.isfile(man):
            copy(self, "debarchiver.1", src=self.build_folder, dst=man1, keep_path=False)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # ★ 显式声明 OpaL 模块的查找路径（PERL5LIB）。
        #
        # 理论上 opalmod 的 runenv_info 应经依赖图自动聚合，但**实测未传播到本包的
        # 消费者**：`conan install --requires=debarchiver/0.11.7 -g VirtualRunEnv`
        # 生成的 runenv 中只有 perl 的 PERL5LIB，**没有任何 opalmod 路径**
        # （对照：单独 `--requires=opalmod/0.2.2.1` 时有 2 条），导致
        #   Can't locate OpaL/action.pm in @INC
        # 故此处显式补上，保证 `env perl` 能真实加载 OpaL::*。
        try:
            opal_pkg = self.dependencies["opalmod"].package_folder
        except Exception:      # noqa: BLE001 — package_info 阶段取不到依赖时静默跳过
            opal_pkg = None
        if opal_pkg:
            for opal_dir in glob.glob(os.path.join(opal_pkg, "lib", "perl5", "**", "OpaL"),
                                      recursive=True):
                if os.path.isdir(opal_dir):
                    # PERL5LIB 需同时含「OpaL 的上一级」（供 use OpaL::xxx 解析）
                    # 与 OpaL 目录本身（AutoLoader 的 auto/ 查找）
                    self.runenv_info.append_path("PERL5LIB", os.path.dirname(opal_dir))
                    self.runenv_info.append_path("PERL5LIB", opal_dir)
            self.output.info(f"debarchiver: PERL5LIB += {opal_pkg} 下的 OpaL 路径")
        else:
            self.output.warning("debarchiver: 未取到 opalmod 的 package_folder，"
                                "OpaL 模块路径未注入（消费者需自行设置 PERL5LIB）")
        self.output.info("debarchiver 已安装到 bin/debarchiver")
