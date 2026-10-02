#!/usr/bin/env python3
"""Conan recipe — intltool-debian 0.35.0-20060710.6 (Debian RFC822 i18n fork).

intltool-debian 是 Debian 用 salsa.debian.org/debian/intltool-debian.git 维护的
intltool 分支，为 Debconf 模板等 RFC822 配置文件做国际化（Debian/Launchpad 系
autotools 库的 po/ 依赖此工具集）。上游版本串为 0.35.0+20060710.6，本配方按
conan 版本规则映射为 0.35.0-20060710.6（见 conandata.yml 注释）。

产物是 3 个纯 Perl 脚本（intltool-extract / intltool-merge / intltool-update），
各自自包含（仅依赖 perl 核心模块 strict/Getopt::Long/Cwd/File::Copy/
File::Basename/File::Find，无需 XML::Parser），无原生编译。上游是极简 Makefile
（all 只 chmod，install 装到 share/intltool-debian），无 configure/autotools/cmake。

适配要点：
- 无原生编译，无 pkg-config 链，无 configure 平台检查——直接打包脚本即可。
- 按 R38 工具型模型把脚本装入 bin/（上游装 share/intltool-debian 是 Debian
  debconf 专用布局；脚本自包含、无同目录依赖，OHOS 作为通用 i18n 工具装到
  bin/ 更符合 Conan tool 约定），package_type=application。
- 运行时依赖：perl 解释器 + gettext 工具链（脚本调 xgettext/msgmerge/msgfmt，
  且支持 XGETTEXT/MSGMERGE/MSGFMT 环境变量覆盖默认 /usr/bin/ 路径）。
- 上游测试：make test → prove --verbose t/*.t（t/syntax.t 对 3 脚本各 perl -wc
  语法检查，3 断言），纯语法检查不涉网络/显示，可真实执行。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches

# 上游 3 个可执行脚本（无原生编译）
SCRIPTS = ["intltool-extract", "intltool-merge", "intltool-update"]


class IntltoolDebianConan(ConanFile):
    name = "intltool-debian"
    version = "0.35.0-20060710.6"
    package_type = "application"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/intltool-debian"
    description = ("intltool-debian — Debian 维护的 intltool fork，为 RFC822/"
                   "Debconf 配置文件提供 i18n（intltool-extract/merge/update）")
    settings = "os", "compiler", "build_type", "arch"
    # 无补丁工程（patches_applied: []）：不上传不存在的 patches/ 目录，
    # export_sources() 仍调用 export_conandata_patches，未来如加补丁无需改结构

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"intltool-debian does not support os={self.settings.os}")

    def requirements(self):
        # 真实运行时依赖：perl 解释器（脚本执行/上游测试的解释器桥）。
        # gettext 工具链由脚本运行时调用，作为运行时依赖一并声明，确保
        # 消费方经 conanrun 获得 xgettext/msgmerge/msgfmt（脚本亦支持
        # XGETTEXT/MSGMERGE/MSGFMT 环境变量覆盖）。
        self.requires("perl/5.42.2.3")
        self.requires("gettext/0.22.5.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 无原生编译，无 configure。唯一“构建”是确保脚本可执行（上游
        # Makefile 的 all 目标亦仅 chmod），并执行上游测试。
        self.run("make all", cwd=self.source_folder)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """上游测试：make test → prove --verbose t/*.t。

        t/syntax.t 用 Test::More 对 3 个脚本各跑 `perl -wc`（语法检查）。
        perl 包的 prove shebang 是 `#!//bin/perl`，HMDFS 无法直接当可执行
        运行（同 intltool 0.51.0 E337 结论），故用 perl 解释器桥显式调用：
        `$PERL <prove> --verbose`，并依赖 conanrun 注入 PERL5LIB（定位
        strict/Test::Harness 核心模块）。
        """
        perl = os.environ.get("PERL") or "perl"
        prove = os.path.join(self.dependencies["perl"].package_folder,
                             "bin", "prove")
        cmd = (f'cd {self.source_folder} && '
               f'"{perl}" {prove} --verbose t/*.t')
        self.run(cmd, env="conanrun")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        missing = []
        for script in SCRIPTS:
            src = os.path.join(self.source_folder, "intltool-bin", script)
            if not os.path.isfile(src):
                # 上游缺脚本属异常：显式报错，避免打包出缺件清单而不自知
                missing.append(src)
                continue
            copy(self, script,
                 src=os.path.join(self.source_folder, "intltool-bin"),
                 dst=bin_dir)
            # 确保可执行位（Conan 拷贝可能剥除）
            target = os.path.join(bin_dir, script)
            os.chmod(target, os.stat(target).st_mode | 0o755)
        if missing:
            raise ConanException(
                "upstream intltool-bin is missing expected scripts: "
                + ", ".join(missing))
        # 许可证/作者信息
        doc_dir = os.path.join(self.package_folder, "share", "doc",
                               "intltool-debian")
        os.makedirs(doc_dir, exist_ok=True)
        copy(self, "AUTHORS", src=self.source_folder, dst=doc_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
