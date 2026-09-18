#!/usr/bin/env python3
"""Conan recipe — dh-shell-completions 0.1.0（脚本包，零编译）。

dh-shell-completions 是 Debian debhelper 的 dh 序列 addon，按各 shell 的约定把
bash / fish / zsh 补全脚本安装到 vendor 目录（等同 dh_bash-completion，但支持多 shell）。
上游 tarball 为 Debian native 源（debian/source/format = 3.0 (native)）：
无 configure / CMake / autotools，文件按 debian/install 布局安装。

上游官方测试在 build() 内真实执行：顶层 Makefile 的 `test` target 驱动
`tests/run.sh gen` / `tests/run.sh composite` / `tests/run.sh separate` 三组用例
（fixture 位于 tests/{gen,composite,separate}/，各自校验 bash/fish/zsh 补全
的安装路径与内容）。测试需要 perl 运行时与 debhelper（dh 命令 + Dh_Lib），
配方在 build 目录内自建测试工具链：

  - perl          HNP 提供（/data/service/hnp/bin/perl，位于 PATH）
  - debhelper     Debian 官方源码 tarball（dh + 全部 dh_* 命令 + Dh_Lib 模块；
                  制品仓的 debhelper 包只装 dh + lib/，缺 dh_* 命令）
  - dh-autoreconf compat 13 默认启用的 autoreconf 序列 addon 由独立源包提供
  - DEB_* 变量    替代 `dpkg-architecture`（OHOS 无 dpkg）

工具链各命令与上游 dh_shell_completions 的 shebang 均适配为
`/usr/bin/env perl`（OHOS 无 /usr/bin/perl）；上游脚本的该处适配以
patches/0001-* 形式留存，上游测试脚本本身未做任何修改。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, chmod, copy, download,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# 上游测试工具链来源（Debian 官方 pool，仅 build() 阶段使用，不进入包产物）
TEST_TOOLCHAIN = {
    "debhelper": {
        "url": "https://deb.debian.org/debian/pool/main/d/debhelper/debhelper_13.3.4.tar.xz",
        "sha256": "5173b6c6d613e7c27a9c378ef339b01438b5bd80a0fc48b235df70307f5c77c6",
    },
    "dh-autoreconf": {
        "url": "https://deb.debian.org/debian/pool/main/d/dh-autoreconf/dh-autoreconf_20_all.deb",
        "sha256": "9527d06ee13195c48718a2580d7262883344a5ecc7a77b48c3b7aa70086a0125",
    },
}

# 目标平台（OHOS aarch64）的 dpkg 架构变量：debhelper 优先读环境变量，
# 未设置时它会 fork `dpkg-architecture`（OHOS 无 dpkg）。
DEB_ARCH_ENV = {
    "DEB_BUILD_ARCH": "arm64",
    "DEB_BUILD_ARCH_OS": "linux",
    "DEB_BUILD_ARCH_CPU": "arm64",
    "DEB_BUILD_ARCH_BITS": "64",
    "DEB_HOST_ARCH": "arm64",
    "DEB_HOST_ARCH_OS": "linux",
    "DEB_HOST_ARCH_CPU": "arm64",
    "DEB_HOST_ARCH_BITS": "64",
    "DEB_BUILD_GNU_TYPE": "aarch64-linux-gnu",
    "DEB_HOST_GNU_TYPE": "aarch64-linux-gnu",
    "DEB_HOST_MULTIARCH": "aarch64-linux-gnu",
}

# 上游官方用例（顶层 Makefile `test` target 的三项，顺序与上游一致）
UPSTREAM_TEST_CASES = ("gen", "composite", "separate")


class DhShellCompletionsConan(ConanFile):
    name = "dh-shell-completions"
    version = "0.1.0"
    description = ("debhelper addon to install shell completions for bash, fish and zsh "
                   "(dh-shell-completions 0.1.0)")
    license = "Apache-2.0"
    homepage = "https://salsa.debian.org/debian/dh-shell-completions"
    url = "https://salsa.debian.org/debian/dh-shell-completions"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _env_perl_shebang(self, path):
        """把 #!/usr/bin/perl 适配为 #!/usr/bin/env perl（OHOS 无 /usr/bin/perl）。"""
        with open(path, "rb") as fh:
            data = fh.read()
        if data.startswith(b"#!/usr/bin/perl"):
            with open(path, "wb") as fh:
                fh.write(b"#!/usr/bin/env perl" + data[len(b"#!/usr/bin/perl"):])
        os.chmod(path, 0o755)

    def _setup_test_toolchain(self):
        """在 build 目录内搭建执行上游 tests/ 的 perl 工具链。

        返回 (工具链 bin 目录, PERL5LIB 值)；两者随 build 目录销毁，不进入包产物。
        """
        tc = os.path.join(self.build_folder, "upstream-test-toolchain")
        tcbin = os.path.join(tc, "bin")
        os.makedirs(tcbin, exist_ok=True)

        # debhelper 官方源码 tarball：dh 脚本 + 全部 dh_* 命令 + Dh_Lib/Sequence 模块
        tar_path = os.path.join(tc, "debhelper.tar.xz")
        download(self, TEST_TOOLCHAIN["debhelper"]["url"], tar_path,
                 sha256=TEST_TOOLCHAIN["debhelper"]["sha256"])
        debhelper_workdir = os.path.join(tc, "debhelper-src")
        os.makedirs(debhelper_workdir, exist_ok=True)
        self.run(f"tar -xf {tar_path} -C {debhelper_workdir}")
        debhelper_root = os.path.join(debhelper_workdir, "debhelper")

        for name in sorted(os.listdir(debhelper_root)):
            if name != "dh" and not name.startswith("dh_"):
                continue
            src = os.path.join(debhelper_root, name)
            if not os.path.isfile(src):
                continue
            shutil.copy(src, os.path.join(tcbin, name))
            self._env_perl_shebang(os.path.join(tcbin, name))

        # dh-autoreconf：compat 13 默认启用的 autoreconf 序列 addon
        deb = os.path.join(tc, "dh-autoreconf.deb")
        download(self, TEST_TOOLCHAIN["dh-autoreconf"]["url"], deb,
                 sha256=TEST_TOOLCHAIN["dh-autoreconf"]["sha256"])
        autoreconf_root = os.path.join(tc, "dh-autoreconf")
        os.makedirs(autoreconf_root, exist_ok=True)
        self.run(f"ar x {deb} && tar -xf data.tar.xz", cwd=autoreconf_root)

        for name in ("dh_autoreconf", "dh_autoreconf_clean"):
            shutil.copy(os.path.join(autoreconf_root, "usr", "bin", name),
                        os.path.join(tcbin, name))
            self._env_perl_shebang(os.path.join(tcbin, name))

        perl5lib = os.pathsep.join([
            os.path.join(debhelper_root, "lib"),
            os.path.join(autoreconf_root, "usr", "share", "perl5"),
        ])
        return tcbin, perl5lib

    def build(self):
        # 纯脚本包：无编译、无构建系统（上游为 Debian native 包）。
        apply_conandata_patches(self)

        tcbin, perl5lib = self._setup_test_toolchain()
        env = Environment()
        for name, value in DEB_ARCH_ENV.items():
            env.define(name, value)
        env.prepend_path("PATH", tcbin)
        env.define("PERL5LIB", perl5lib)
        # OHOS /tmp 只读，perl/debhelper 的临时目录落在 build 目录内
        env.define("TMPDIR", self.build_folder)

        # 上游官方用例实跑（任一失败 self.run 抛错 → 构建失败）
        with env.vars(self).apply():
            for case in UPSTREAM_TEST_CASES:
                self.output.info(f"上游用例 tests/run.sh {case}")
                self.run(f"tests/run.sh {case}", cwd=self.source_folder)
                self.output.info(f"上游用例 tests/run.sh {case} => PASS")

    def package(self):
        # 镜像 Debian 安装布局（见 debian/install）到 Conan 包前缀：
        #   dh_shell_completions  → bin/dh_shell_completions          (0755)
        #   shell_completions.pm  → share/perl5/Debian/Debhelper/Sequence/shell_completions.pm
        # 说明：手册页 dh_shell_completions.1 由 debian/rules 用 pod2man 生成（依赖 perl），
        # 故不生成、不安装该手册页（不依赖 pod2man）。
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "dh_shell_completions", src=self.source_folder, dst=bindir)
        chmod(self, os.path.join(bindir, "dh_shell_completions"), 0o755)
        copy(self, "shell_completions.pm", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "perl5",
                              "Debian", "Debhelper", "Sequence"))

    def package_info(self):
        # application/CLI：包内无库产物，不声明 cpp_info.libs
        self.cpp_info.bindirs = ["bin"]
