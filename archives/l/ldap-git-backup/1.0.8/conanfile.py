#!/usr/bin/env python3
"""Conan recipe for ldap-git-backup 1.0.8 — snapshots LDAP directory LDIF
dumps into a Git repository.

Upstream (github.com/elmar/ldap-git-backup) is an autotools wrapper around
two pure-Perl scripts: `ldap-git-backup` (main tool) and `safe-ldif`
(slapcat wrapper), plus a prove-driven test suite `t/` (11 cases with a
mock-slapcat helper — no live LDAP server needed). The autotools machinery
only substitutes @sbindir@/@abs_top_builddir@/@abs_top_srcdir@ in the `.in`
templates and sets the executable bit (AC_CONFIG_FILES + Makefile `edit`
rule); there is no compilation. This recipe performs the same substitutions
directly in build(), so autoconf/automake are not required on the build
machine (OHOS devices have no autotools).

Runtime deps: perl (core modules only) + Git.pm (ships with git).
License: GPL-3.0-or-later.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# 上游 t/ 测试文件清单（编译期防漂移校验 + 替换清单共用）
UPSTREAM_TESTS = (
    "001_help-option", "010_read_ldif", "020_entry-name",
    "030_git-from-scratch", "031_backup-to-existing-dir",
    "040_delete-entry", "050_modify-entry", "060_custom_commit",
    "061_no_change", "070_mock-slapcat", "071_safe-ldif",
)

# 上游脚本 OHOS 兼容补丁（Git.pm command() 空上下文管道竞态，见 notes.md
# 真机记录第 5 条）。(old, new, 锚点说明) —— build() 替换时校验 old 恰出现
# 1 次，防上游版本漂移。
PATCH_RM_CALL = (
    "$repo->command('rm', (keys %files_before)) if %files_before;",
    ("my @deleted = $repo->command('rm', (keys %files_before)) "
     "if %files_before;"),
    "void-context rm call",
)


class LdapGitBackupConan(ConanFile):
    name = "ldap-git-backup"
    version = "1.0.8"
    description = "Back up an LDAP directory into a Git repository"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/elmar/ldap-git-backup"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # R32: 显式 allow-list。纯 Perl 脚本（核心模块 + Git.pm），Linux/OHOS 均可。
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ldap-git-backup supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 脚本运行时唯一语言依赖：perl（Git.pm 随 git 系统工具提供）。
        # 仓库已适配 perl/5.42.2.3（OHOS 预编译包）。
        self.requires("perl/5.42.2.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # 配方自足：源码全部经 conandata sources 下载，无本地文件随配方导出。
        pass

    def _check_inventory(self):
        """构建期防漂移校验（kicad-demos 先例范式）。"""
        src = self.source_folder
        for rel in ("ldap-git-backup.in", "safe-ldif.in", "configure.ac",
                    "Makefile.am", "COPYING", "t/test-helper.pm.in",
                    "t/mock-slapcat.in"):
            if not os.path.isfile(os.path.join(src, rel)):
                raise ConanInvalidConfiguration(
                    f"ldap-git-backup 1.0.8 inventory drift: missing {rel}"
                )
        for name in UPSTREAM_TESTS:
            if not os.path.isfile(os.path.join(src, "t", f"{name}.t.in")):
                raise ConanInvalidConfiguration(
                    f"ldap-git-backup 1.0.8 inventory drift: missing t/{name}.t.in"
                )
        testdata = os.path.join(src, "t", "testdata")
        if sum(len(fs) for _, _, fs in os.walk(testdata)) != 15:
            raise ConanInvalidConfiguration(
                "ldap-git-backup 1.0.8 inventory drift: t/testdata file count != 15"
            )

    def build(self):
        """上游 configure/Makefile 的等价物：@VAR@ 替换 + 可执行位 + shebang。

        上游 AX_CONFIG_FILE_EXEC 生成的测试树保持原相对布局（脚本 + t/），
        @abs_top_builddir@/@abs_top_srcdir@ 统一指向安装后的
        share/ldap-git-backup，消费者在该目录 prove t 即可复跑上游套件。

        shebang：上游 `#!/usr/bin/perl` 在 OHOS 不可用——/usr/bin/perl 不存在，
        且实测 `#!/usr/bin/env perl` 报 "bad interpreter: Permission denied"
        （OHOS 禁止 env 解释器）。故对会被 exec 的脚本重写为 conan perl
        依赖包的绝对路径（缓存路径 <128B，在 BINPRM 限制内）；prove 用
        $^X 调起 .t 文件、test-helper.pm 经 require 加载，均不走 shebang。

        补丁：PATCH_RM_CALL 将删除路径的 Git.pm 调用由空上下文改为列表
        上下文——OHOS 上 git rm 被 SIGPIPE 杀死致删除失效（见 notes.md
        真机记录第 5 条）；锚点计数校验防上游版本漂移。
        """
        self._check_inventory()
        src = self.source_folder
        out = os.path.join(self.build_folder, "out")
        share = os.path.join(self.package_folder, "share", "ldap-git-backup")
        os.makedirs(os.path.join(out, "t"), exist_ok=True)
        perl_bin = os.path.join(self.dependencies["perl"].package_folder,
                                "bin", "perl")

        mapping = {
            # 上游 configure --sbindir：safe-ldif 默认落点（可被 --ldif-cmd 覆盖）
            "sbindir": os.path.join(self.package_folder, "bin"),
            "abs_top_builddir": share,
            "abs_top_srcdir": share,
        }

        def substitute(src_rel, dst_rel, shebang=False, patches=()):
            with open(os.path.join(src, src_rel), encoding="utf-8") as fh:
                content = fh.read()
            for name, value in mapping.items():
                content = content.replace(f"@{name}@", value)
            if shebang and content.startswith("#!/usr/bin/perl"):
                content = f"#!{perl_bin}" + content[len("#!/usr/bin/perl"):]
            for old, new, why in patches:
                n = content.count(old)
                if n != 1:
                    raise ConanInvalidConfiguration(
                        f"ldap-git-backup patch anchor drift: {why} found {n}x"
                    )
                content = content.replace(old, new)
            dst = os.path.join(out, dst_rel)
            with open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
            os.chmod(dst, 0o755)

        # 会被 exec 的脚本重写 shebang：bin/ 两个直执行入口 +
        # t/mock-slapcat（主脚本/safe-ldif 以 `open ... '-|'` 经 sh exec
        # --ldif-cmd 的值，071_safe-ldif.t 正是这样调起 mock-slapcat）
        substitute("ldap-git-backup.in", "ldap-git-backup", shebang=True,
                   patches=(PATCH_RM_CALL,))
        substitute("safe-ldif.in", "safe-ldif", shebang=True)
        substitute("t/mock-slapcat.in", "t/mock-slapcat", shebang=True)
        substitute("t/test-helper.pm.in", "t/test-helper.pm")
        for name in UPSTREAM_TESTS:
            substitute(f"t/{name}.t.in", f"t/{name}.t")
        shutil.copytree(os.path.join(src, "t", "testdata"),
                        os.path.join(out, "t", "testdata"))

    def package(self):
        out = os.path.join(self.build_folder, "out")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)  # copy2 不自建父目录
        for name in ("ldap-git-backup", "safe-ldif"):
            shutil.copy2(os.path.join(out, name), os.path.join(bindir, name))
        # 上游测试树随包安装：share/ 下保持上游相对布局（脚本 + t/ + 数据），
        # @abs_*@ 已指向该目录，消费者 cd 后 prove t 原样复跑。
        share = os.path.join(self.package_folder, "share", "ldap-git-backup")
        os.makedirs(share, exist_ok=True)  # copy2 不自建父目录
        for name in ("ldap-git-backup", "safe-ldif"):
            shutil.copy2(os.path.join(out, name), os.path.join(share, name))
        copy(self, "*", src=os.path.join(out, "t"), dst=os.path.join(share, "t"))
        copy(self, "README.mdown", src=self.source_folder,
             dst=os.path.join(share, "docs"))
        copy(self, "ChangeLog", src=self.source_folder,
             dst=os.path.join(share, "docs"))
        copy(self, "*", src=os.path.join(self.source_folder, "examples"),
             dst=os.path.join(share, "examples"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        # 纯脚本包与 os/arch/compiler 无关 → 单一 package_id（headeronly 模板变体 C）
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
