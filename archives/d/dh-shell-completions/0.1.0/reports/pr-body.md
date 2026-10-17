## PR 信息
- **三方库名称**：dh-shell-completions
- **上游版本**：0.1.0
- **上游仓库地址**：https://salsa.debian.org/debian/dh-shell-completions
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无单元测试框架 |
| 集成测试 | 3 | 来源：顶层 `Makefile` 的 `test` target → `tests/run.sh <case>`（`test-gen` / `test-composite` / `test-separate`，fixture 位于 `tests/{gen,composite,separate}/`） |
| 其他测试 | 0 | 上游无 `debian/tests/`（无 DEP-8 autopkgtest） |
| **合计** | **3** | 上游官方测试全量清单 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | — |
| 集成测试 | 3 | 不变 | 上游 3 组用例在 OHOS 上实跑通过（3/3）：配方 `build()` 内搭建 perl + debhelper 测试工具链后执行 `tests/run.sh gen\|composite\|separate` |
| 鸿蒙特有测试 | 10 | 新增 | `test_package` 消费者断言：包产物存在性 + 内容标记（10/10 通过） |
| **合计** | **13** | **+10** | 上游 3/3 实跑通过 + 消费者断言 10/10 通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

> 上游 `tests/run.sh`、`tests/{gen,composite,separate}/` fixture 与顶层 `Makefile` 全部原样保留、
> 未做任何改动；用例中的断言（补全文件的安装路径与内容）均为上游原始断言。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖

> 上游官方 3 组用例已覆盖 `dh_shell_completions` 的三种工作模式（generation/composite/separate）
> 并全部实跑通过；适配侧另加 10 条包产物消费者断言（`test_package`，见「补充说明」），
> 属本仓库标准的消费者验证层，不属「上游无测试用例」的补全场景。

## 验证结果

- 编译状态：**通过**（零编译；`conan create` 干净构建，os=OHOS aarch64，exit 0）
- 上游测试用例通过率：**3/3（100%）** —— `tests/run.sh gen|composite|separate` 在 OHOS 上真实执行通过
- 新增测试用例通过率：**10/10（100%）**

## 补充说明

**上游测试执行（R51 三步法）**：上游官方用例 N=3（`tests/run.sh gen|composite|separate`，
即顶层 `Makefile` 的 `test` target），上游无 `debian/tests/`（无 DEP-8）。三组用例已在
`build()` 内**真实执行并通过 3/3**（任一失败即构建失败）。测试所需依赖及 OHOS 上的获取方式：

| 依赖 | OHOS 上的来源 |
|------|---------------|
| perl 5.42.0 | HNP 提供：`/data/service/hnp/bin/perl`（位于 PATH） |
| debhelper 13.3.4（`dh` + 全部 `dh_*` + `Dh_Lib`/`Sequence`） | debhelper 官方源码 tarball（deb.debian.org，sha256 固定） |
| dh-autoreconf 20（compat 13 默认启用的 `autoreconf` 序列 addon） | dh-autoreconf 官方 `.deb`（deb.debian.org，sha256 固定） |
| `dpkg-architecture` | 不需要：以 `DEB_*` 环境变量替代（OHOS 无 dpkg） |

**源码修改 1 处**（非测试文件）：`dh_shell_completions` 的 shebang `#!/usr/bin/perl` →
`#!/usr/bin/env perl`（`patches/0001-dh_shell_completions-env-perl-shebang.patch`）。原因：OHOS 无
`/usr/bin/perl`，perl 由 HNP 提供且位于 PATH，原 shebang 会导致 `bad interpreter`，脚本与本包
上游测试均无法执行。上游测试脚本本身未做任何修改。

**包形态**：Debian native 纯 Perl 脚本包（`debian/source/format` = `3.0 (native)`），零编译；
`package_type=application`，`package()` 镜像 Debian 安装布局（`debian/install` →
`bin/dh_shell_completions`、`share/perl5/Debian/Debhelper/Sequence/shell_completions.pm`）。

**验证证据**：`reports/conan-create.log`（3 组上游用例 `=> PASS` + test_package 断言）、
`reports/w3-local-ci.log`（L0/L1/L2/L4/L5 + L1e 破坏性反证，Pass rate 100% (1/1)）、
`reports/conan-verify-report.md`、`reports/test-report.md`。

**已知限制**：手册页由上游 `debian/rules` 用 `pod2man` 生成，配方不生成、不安装；
CI 的 L2 `--version` 冒烟探测为警告级非阻断（该探测需 debhelper 的 `Dh_Lib`，
debhelper 是本包运行时依赖，不在包内）。

**其他**：源码为 Debian 官方 pool（R39）
`https://deb.debian.org/debian/pool/main/d/dh-shell-completions/dh-shell-completions_0.1.0.tar.xz`
（`sha256=9f90f4122198336a8917d77d1e6e408a3506fbecb7300fbcf58145f4f61b120f`）；
许可证 Apache-2.0（`LICENSE` 与 `debian/copyright` 一致）；
`lang-preflight` 因顶层 `Makefile` 启发式判 `detected=mixed`（**假阳性**，实测无任何 C/C++ 源），
已如实记录于 `notes.md`。
