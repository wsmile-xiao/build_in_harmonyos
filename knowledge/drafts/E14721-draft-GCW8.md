# E14721 — autotools 包装的纯 Perl 包：目标架构 perl 在 x86 构建机/runner 上不可执行

> **状态**: 草稿（协作者产出，未 promote）｜ **kv**: `knowledge/drafts/E14721-draft-GCW8.kv`
> **来源实例**: sproxy 1.02 ｜ **通用性**: 适用于任何 autotools/Makefile 包装的纯 Perl 脚本包

## 错误特征

```
aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1': No such file or directory
Can't load '/…/perl/p/lib/perl5/5.42.2/aarch64-linux-thread-multi/auto/Socket/Socket.so' for module Socket
Can't locate JoeDog/Config.pm in @INC          # 设备上运行期
```

## 触发条件

- 构建系统: autotools（`configure.in` / `Makefile.am`）包装的纯 Perl 脚本，无 C/C++ 编译
- 阶段: configure/make（模块探测）与 test_package（运行脚本）
- 环境: x86 构建机/runner + 交叉 profile `ohos-aarch64`，perl 依赖为 aarch64 musl ELF（见 E544）

## 根因分析

1. **上游探测在构建期执行目标 perl**：sproxy `configure.in` 用 ``haveconfig=`$PERL utils/modtest JoeDog::Config` ``，
   结果（yes/no）写入 `lib/Makefile`，`if test $(haveconfig) = "no"` 才会解包并安装自带的 JoeDog::Config。
   交叉构建时 `$PERL` 跑不起来，输出为空 ≠ "no"，自带模块被**静默跳过**——`make install` 成功，包却缺模块。
2. **PERL5LIB 污染**：`conanrun` 会导出依赖 perl 的 `PERL5LIB`（含 aarch64 XS 目录）。测试里为了真正运行脚本
   而改用主机 perl 时，继承该变量，加载 Socket/Cwd 等 XS 模块即失败，连 `use LWP::UserAgent` 都过不了。

## 解决方案

### 推荐方案

- **构建**：不跑上游 configure/Makefile。`build()` 里用 Python 复刻其 `sed` 替换（`%_VERSION%` 等）、把 shebang 改成依赖 perl
  的绝对路径（OHOS 无 `/usr/bin/perl` 且禁 `env perl`），并用 `tarfile` 直接从 `lib/*.tar.gz` 取出自带的纯 Perl `.pm`
  安装到 `lib/<pkg>/`。构建机因此不需要 autoconf/automake/libtool，也不需要能运行目标 perl。
- **测试**：候选 perl（shebang 所指依赖 perl、`$PERL`、`which perl`、`/usr/bin/perl`…）逐个用
  `perl -e 'use LWP::UserAgent; use HTTP::Daemon'` 试载，**只对 shebang 所指的依赖 perl 继承 conanrun 的 PERL5LIB**，
  其余候选用干净的 PERL5LIB（仅包内 `lib/<pkg>`），第一个能载入的用于跑完整消费者流程。

### 备选

- 探测必须保留时，用构建机（`-pr:b`）perl 探测，并通过 configure 变量（`haveconfig=no` 等）显式传入结果。

### 禁止做法

- ❌ 把 `/usr/bin/perl` 软链给目标 perl 用，或把污染的 PERL5LIB 原样带给主机 perl
- ❌ 只 `grep`/`ls` 检查 `.pm` 文件存在就当测试（rule12 判 N=0）

## 验证

```bash
# x86 runner 上依赖 perl 不可执行（E544）
$CONAN_HOME/p/perl*/p/bin/perl -e 1     # aarch64-binfmt-P: Could not open '/lib/ld-musl-aarch64.so.1'
# 包内自带模块已安装
ls $PKG/lib/sproxy/JoeDog/Config.pm
# 消费者测试端到端（GET/POST 经代理转发 + 输出文件 URL 行）
conan create archives/s/sproxy/1.02 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 关联条目

- 相关: E544（x86 runner 上 OHOS 动态产物无法运行）、`DRAFT-ohos-perl-script-package-conan-adaptation`（shebang / @INC 陷阱）
