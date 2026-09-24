# DRAFT：上游 CUnit 套件 + 兄弟二进制（checkpolicy）——在配方内真实执行的接入清单

> Contributor: CIW | Status: Draft | Updated: 2026-09-21
> Source: libsepol 3.11 适配（PR #11650 的 rule4「上游 28 用例 0 执行」整改）
> 同 stem 知识文件：`DRAFT-libsepol-3.11-upstream-cunit-suite-with-sibling-tool.kv`

## 错误特征

赛题审查 rule4 判 FAIL：`上游有用例 28 个但一个也没测（0/28）`、`少报: 上游实测 N=28 > 声明 N=0`。
而配方侧写的是「上游 Makefile 无 check/test 目标」——**两边都没说谎**：上游确有一个 `test:` 目标，
但它**依赖三样配方默认不提供的东西**，于是"有测试入口 ≠ 能执行"，被清点进 N 却从未跑起来。

## 根因分析（三重前置，缺一即不可执行）

以 libsepol 3.11 为例，`libsepol/tests/Makefile` 的 `test:` 目标要求：

1. **CUnit 单元测试框架**：链接 `-lcunit`（`:51`），驱动 `libsepol-tests.c:29-31` 直接 `#include <CUnit/Basic.h>`。
   配方若不声明 CUnit 依赖，链接期即失败。
2. **同源码树的兄弟二进制**：`test:` 目标调用 `../../checkpolicy/checkpolicy -M ... -o ...`（`:70-72`）
   来生成测试策略 ⇒ **必须先构建 `checkpolicy`**（它在上游同一 tarball 内，但不属于本包制品）。
3. **m4 预处理**：policy 由 `%.conf` 经 `%.conf.std` / `%.conf.mls` 规则用 **m4** 生成（`:53/:56`），
   缺 m4 则 policy 造不出来，套件会在准备阶段失败。

> 结论：**"上游有 test 目标但配方跑不了"是这类"套件 + 兄弟工具 + 预处理"型仓库的通病**；
> 先把三重前置补齐，再谈通过率，否则永远停在 0 执行。

## 推荐方案

**方法**: satisfy-cunit-and-sibling-tool-then-run-upstream-test-target

1. **声明测试框架依赖**：`test_requires("cunit/<可用版本>")`（本仓 `archives/c/cunit` 已有 0.11.0/0.15.2）。
   用 `self.dependencies.test["cunit"].cpp_info.aggregated_components()` 取 `includedirs/libdirs/libs`，避免硬编码。
2. **先构建兄弟工具**：在 `build()` 中、跑套件之前 `make -C <src>/checkpolicy …`（同 tarball，无需外部依赖）。
3. **跑上游 `test:` 目标**：`make -C <src>/libsepol/tests test`（必要时传 `CC=`/`CFLAGS=` 与 CUnit 的 `-I/-L/-l`）。
4. **把数字写进四处**：正文两张表 + 验证结果 + notes/manifest，口径 `N_static=入口数`、`N_executed=真跑数`、
   未执行项逐项给技术原因与**官方源码包下的实测报错原文**。

**验证/命令**

```bash
# 决定性证据（证明"有 test 目标但默认跑不起来"）
grep -n 'lcunit'            libsepol/tests/Makefile      # → 51
grep -n 'checkpolicy'       libsepol/tests/Makefile      # → 70-72（兄弟二进制）
grep -n 'conf.std\|conf.mls' libsepol/tests/Makefile     # → 53/56（m4 预处理）
# 真跑（配方内或手工）
make -C checkpolicy && make -C libsepol/tests test
```

## 适用范围与反例

- **适用**：上游自带测试套件、但套件依赖"测试框架 + 同仓兄弟二进制 + 预处理工具"三位一体的仓库；
  尤其是 SELinux 家族（libsepol / checkpolicy / secilc / libselinux）——它们共享同一套 `tests/` 布局与 `checkpolicy` 依赖。
- **反例/边界**：
  - 若套件需要**内核特权**（加载 SELinux 策略、mount ns）则部分用例在 CI 容器内不可行 ⇒ **逐项**给技术原因，不得整体记 0 执行；
  - 若兄弟工具**不在同一 tarball**（需单独下载）⇒ 先按 E150 取子模块/独立包，再谈执行；
  - 不要把"我们没接"归类为"上游不可执行"——证据必须是**官方源码包下的构建/运行报错原文**。

## 验证证据（libsepol 3.11 / PR #11650）

- `libsepol/tests/Makefile:51`：`$(CC) $(LDFLAGS) $(objs) $(parserobjs) -lcunit $(LIBSEPOL) -o $@`
- `libsepol/tests/Makefile:70-72`：`test:` 目标调用 `../../checkpolicy/checkpolicy -M policies/test-cond/refpolicy-base.conf ...`
- `libsepol/tests/libsepol-tests.c:29-31`：`#include <CUnit/Basic.h> / <CUnit/Console.h> / <CUnit/TestDB.h>`
- 上游用例清点：`libsepol/tests/` 下 17 个 `.c`（含 `test-*.c` 与驱动）+ 37 个 policy `.conf`；
  机器人实测 N=28（以套件注册入口计）
- 本仓 `archives/c/cunit` 已有 0.11.0 / 0.15.2 ⇒ 依赖可得，无需自建

## 与既有条目的差异（查重结论）

- `knowledge/doc/*` 与 `knowledge/drafts/*` **均无任何条目提及 `CUnit` 或 `checkpolicy`**（2026-09-21 实测 grep）；
  泛型条目 E046(`skip-test`)/E018(`wrapper-script`) 讲的是"跳过/包装"，**不是"补齐前置后真实执行"**，签名与解法都不同 ⇒ 本条目按 **create** 申报。
- **`draft-review` 相似度提示已逐条核实**：工具报 `merge-into → E213`，实查 **E213 = `l64a() missing in OHOS libc (musl)`**，讲的是 OHOS musl 缺 libc 符号，与本条（测试框架/兄弟工具/套件执行）**无任何交集**，属关键词相似度误报 ⇒ 维持 **create**。
- 家族关联：与 `DRAFT-mrboom-5.5-upstream-test-entry-unbuildable`（上游测试入口"存在但不可构建"的两类解释与取证口径）互为姊妹条目——
  本条补的是**第三类**：**入口可构建，但缺测试框架/兄弟工具/预处理依赖**。
