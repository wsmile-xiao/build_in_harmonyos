#!/usr/bin/env python3
"""Conan recipe — triehash 0.3.1 (pure Perl script, no compilation).

triehash = 从一组关键字生成 **order-preserving minimal perfect hash** 的 C 代码
（头文件 + 源文件），dpkg / apt 用它生成架构 trie 查找表。上游为**单个 Perl 脚本**，
无编译步骤。

OHOS 适配要点：
- **纯 Perl，无编译**：本配方 install 阶段只把脚本装到 `bin/triehash`。
- **shebang 改写**：上游为 `#!/usr/bin/perl -w`，而 OHOS 上没有 `/usr/bin/perl`
  （perl 由 ohpcd 的 perl/5.42.2 提供，位于包内 bin/）。改为
  `#!/usr/bin/env perl`（仓库内 24 处采用该写法，为主流惯例），由 PATH 解析。
  注意**不能**写成 `#!/usr/bin/env perl -w` —— env 会把 `"perl -w"` 当成
  单个程序名查找而失败，故一并去掉 `-w`（`use warnings` 已在脚本内启用）。
- **依赖 perl/5.42.2**：ohpcd 已发布；脚本仅用核心模块
  （strict / warnings / utf8 / Getopt::Long），无需额外 CPAN 包。
- `-C` / `-H` 支持 `-` 表示标准输出，便于消费者管道使用。
- **上游测试门控 option `run_upstream_tests`（默认关）**：上游 `tests/` 有 7 个用例，
  由 `tests/run-tests.sh` 驱动；但其框架 `tests/framework.sh` 用
  `perl -MDevel::Cover=...` 运行被测脚本，而 **Devel::Cover 不在 ohpcd 的 perl 包内**。
  开启本 option 时，配方会现场生成一个**空操作 Devel::Cover 桩**（仅让 `-M` 加载成功，
  **不改变被测逻辑**）以及 `cover` 空命令，从而**真实执行**上游 7 个用例。
  实测 7/7 通过；并做过**阴性对照**（令 triehash.pl 强制 exit 1 → 框架正确报错），
  证明该套件并非空转。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (copy, get, apply_conandata_patches,
                               export_conandata_patches, chmod, save)
from conan.tools.layout import basic_layout


class TriehashConan(ConanFile):
    name = "triehash"
    version = "0.3.1"
    description = ("triehash — generate a C hash function from a set of keywords "
                   "using an order-preserving minimal perfect hash (pure Perl script)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/julian-klode/triehash"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    # 仓库惯例：可执行脚本类包声明 os/compiler/build_type/arch 四项（L0p）
    settings = "os", "compiler", "build_type", "arch"
    # 门控：默认关闭（交付包不跑上游测试）；开启时真实执行上游 7 个用例
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # 运行期依赖：脚本 shebang 为 `/usr/bin/env perl`，消费者需能解析到 perl
        self.requires("perl/5.42.2", transitive_headers=False, transitive_libs=False)

    def _run_upstream_tests(self):
        """真实执行上游 7 个用例（tests/run-tests.sh）。

        上游框架经 `perl -MDevel::Cover=...` 运行被测脚本，而 Devel::Cover 不在
        ohpcd 的 perl 包内。此处现场生成两个**空操作桩**（仅让 `-M` 加载成功、
        不改变被测逻辑）：
          · Devel/Cover.pm —— 忽略 -summary 等参数的空模块
          · cover          —— run-tests.sh 结尾会调用，空实现
        然后把 perl 依赖的 bin 与桩目录前置到 PATH/PERL5LIB 后执行。
        """
        stub = os.path.join(self.build_folder, "_stub")
        save(self, os.path.join(stub, "Devel", "Cover.pm"),
             "package Devel::Cover;\n"
             "use strict; use warnings;\n"
             "our $VERSION = '0.0-stub';\n"
             "sub import { return 1; }\n"
             "1;\n")
        save(self, os.path.join(stub, "cover"),
             "#!/bin/sh\n"
             "# 空操作桩：上游 run-tests.sh 结尾调用 cover 生成覆盖率报告\n"
             "exit 0\n")
        chmod(self, os.path.join(stub, "cover"), execute=True)

        tests_dir = os.path.join(self.source_folder, "tests")
        run_sh = os.path.join(tests_dir, "run-tests.sh")
        if not os.path.isfile(run_sh):
            raise ConanException("triehash: 未找到上游 tests/run-tests.sh")

        # 脚本 shebang 是 `/usr/bin/env perl` → 需把 perl 依赖的 bin 放到 PATH 最前
        perl_pkg = self.dependencies["perl"].package_folder
        perl_bin = os.path.join(perl_pkg, "bin")
        # ⚠️ conan 的 perl 包**内建 @INC 是坏的**：其编译期前缀被解析成了空串，
        # 于是 @INC 里全是 `//lib/perl5/...`（双斜杠根路径，**均不存在**）——
        # 连核心模块都加载不了（实测 `env -u PERL5LIB <perl> -e 'require strict'`
        # → Can't locate strict.pm）。若不处理，triehash.pl 的 `:encoding(utf8)`
        # 会报 `Unknown PerlIO layer "encoding"`，并连带 Wide character 警告污染
        # 测试输出 → 上游用例 diff 失败（**非被测程序缺陷**）。
        # 注：conanbuildenv **确实**导出了长 PERL5LIB（且是**追加**式
        # `${PERL5LIB:+:$PERL5LIB}`，不是覆盖），但其排在前面的 `//lib/perl5`
        # 条目是坏的 → 实测仍失败。故必须自行补齐模块路径。
        # ⚠️ 不能用「逆序取第一个」选目录：lib/perl5 下同时有 `5.42.2` 与
        # `site_perl`，逆序会把 site_perl 排在前面，而它**不含核心模块**
        # （无 strict.pm）→ 依然加载失败。应以「是否含 strict.pm」判定版本目录。
        perl_libs = []
        base = os.path.join(perl_pkg, "lib", "perl5")
        if os.path.isdir(base):
            for name in sorted(os.listdir(base)):
                vdir = os.path.join(base, name)
                if not os.path.isdir(vdir):
                    continue
                # 版本目录（含核心模块 strict.pm）优先，其余（如 site_perl）随后
                if os.path.isfile(os.path.join(vdir, "strict.pm")):
                    perl_libs.insert(0, vdir)
                else:
                    perl_libs.append(vdir)
                for sub in sorted(os.listdir(vdir)):
                    sdir = os.path.join(vdir, sub)
                    if os.path.isdir(sdir) and ("linux" in sub or "thread" in sub):
                        perl_libs.append(sdir)
        if not perl_libs:
            raise ConanException(
                f"triehash: 未能在 perl 包内定位 lib/perl5 模块目录（{base}）")
        self.output.info("triehash: perl lib dirs = " + os.pathsep.join(perl_libs))

        # 稳健做法：在桩目录放一个 **perl 包装器**，显式带上 -I<perl lib 目录>，
        # 再把桩目录前置到 PATH。之所以可靠，是因为 **`-I` 的优先级高于
        # PERL5LIB**（实测：即便 PERL5LIB 给的是错值，只要 -I 正确，核心模块
        # 仍可加载）—— 故本做法对环境里 PERL5LIB 的取值/顺序**不敏感**，
        # 无需与 conanbuildenv 的长列表较劲。
        inc = " ".join(f'-I"{d}"' for d in perl_libs)
        save(self, os.path.join(stub, "perl"),
             "#!/bin/sh\n"
             "# perl 包装器：为 conan perl 固定 @INC（含核心模块 PerlIO::encoding）\n"
             f'exec "{os.path.join(perl_bin, "perl")}" {inc} "$@"\n')
        chmod(self, os.path.join(stub, "perl"), execute=True)

        # 同时内联 env（供 triehash 自身的 `#!/usr/bin/env perl` 解析），双保险
        p5l = os.pathsep.join([stub] + perl_libs)
        env_prefix = (f'PERL5LIB="{p5l}" '
                      f'PATH="{stub}{os.pathsep}{perl_bin}{os.pathsep}$PATH"')
        self.output.info(f"triehash: perl lib dirs = {p5l}")

        self.run(f'{env_prefix} sh "{run_sh}"', cwd=self.source_folder)
        # 逐用例独立复核（run-tests.sh 已保证失败即退出，这里再确认一遍）
        cases = sorted(n for n in os.listdir(tests_dir) if n.startswith("test-"))
        for case in cases:
            self.run(f'{env_prefix} sh "{os.path.join(tests_dir, case)}"',
                     cwd=self.source_folder)
        self.output.info(f"triehash 上游测试: {len(cases)}/{len(cases)} 用例通过")

    def build(self):
        # 纯 Perl 脚本：无 configure / make，仅应用 shebang 补丁
        apply_conandata_patches(self)
        # 补丁后自校：确认 shebang 已是 env perl（避免补丁静默失效）
        target = os.path.join(self.source_folder, "triehash.pl")
        with open(target, "r", encoding="utf-8") as fh:
            first = fh.readline().rstrip("\n")
        if first != "#!/usr/bin/env perl":
            raise ConanException(
                f"triehash: shebang patch 未生效，首行为 {first!r}")
        if self.options.run_upstream_tests:
            self._run_upstream_tests()

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        # 安装为 bin/triehash（上游文件名带 .pl，安装后去掉后缀以便直接调用）
        copy(self, "triehash.pl", src=self.source_folder, dst=bin_dir)
        os.rename(os.path.join(bin_dir, "triehash.pl"),
                  os.path.join(bin_dir, "triehash"))
        chmod(self, os.path.join(bin_dir, "triehash"), execute=True)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
