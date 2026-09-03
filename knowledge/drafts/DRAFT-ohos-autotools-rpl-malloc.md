# DRAFT-ohos-autotools-rpl-malloc — autotools 交叉编译 AC_FUNC_MALLOC 的 rpl_malloc 误判与缓存变量覆盖

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: 🟡 medium | **Category**: autotools / configure / cross-compile / malloc

## 相关既有条目（同族差异化定位）

本 skill 与既有 "autotools 交叉编译缓存变量" 及 "gettext" 条目共享交叉编译/配置层背景，但本条目是 **`AC_FUNC_MALLOC` 的 `rpl_malloc` 误判**——非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **ats2-postiats #6257 教训**（`ac_cv_prog_cc_works=yes`+`ac_cv_prog_cc_cross=yes`） | 记忆/社区经验 | 交叉编译下 `AC_PROG_CC` 的编译探测（conftest）因沙箱无法运行/无编译器而误判 | 同族（都是交叉编译缓存变量覆盖），但**符号不同**——那是 CC 探测（works/cross），本条目是 **malloc 运行时探测（malloc_0_nonnull）**；触发点、错误特征、修法均不同 |
| **E085**（musl pthread 取消族） | 正式收录 | musl 缺 pthread_cancel 族符号（链接期） | 非本题——那是 **pthread 符号缺失**，本条目是 **configure 运行时探测误判**导致链接 rpl_malloc |
| **E041/E248**（automake 缺失 / Makefile.in mtime 倒挂） | 正式收录 | patch 触及 Makefile 时 make 重生成 automake | 非本题——那是 **构建系统重生成**，本条目是 **configure 探测值误判**（rpl_malloc），与 automake 无关 |
| **DRAFT-ohos-gi18n-gettext-identity-macro**（polkit） | 草稿 | gettext 编译期未声明（恒等宏） | 非本题——那是 **头文件宏**，本条目是 **configure 缓存变量**（malloc），问题层完全不同 |

> 全库查证（2026-09-03）：`rpl_malloc` / `ac_cv_func_malloc_0_nonnull` / `ac_cv_func_malloc` 命中 0 条——无正面撞车；本条目为真增量。

## Scope（何时用）

在 OHOS（或任何不能运行 host 测试程序的交叉编译环境）上用 autotools 构建、且 `configure.ac` 用了 `AC_FUNC_MALLOC` / `AC_FUNC_REALLOC` 的库时，若出现：

- 链接报 `undefined symbol: rpl_malloc`（或 `rpl_realloc`）；
- configure 日志里 `ac_cv_func_malloc_0_nonnull=no`（交叉编译默认）；
- 已确认目标平台（musl/glibc）的 `malloc(0)` 实际返回非 NULL 且正常。

典型实例：speech-dispatcher/0.12.1（`speech-dispatcher` daemon 链接失败）。

## Symptom

```text
ld.lld: error: undefined symbol: rpl_malloc
clang-15: error: linker command failed with exit code 1
# configure 日志: ac_cv_func_malloc_0_nonnull=no （交叉编译无法实测 → 默认）
```

## Root Cause

1. autoconf 的 `AC_FUNC_MALLOC` 用运行测试程序探测 `malloc(0)` 是否返回非 NULL，
   结果存 `ac_cv_func_malloc_0_nonnull`；
2. **交叉编译**（`--host` ≠ `--build`，如 OHOS clang 交叉 aarch64）无法运行 host
   测试程序，该缓存变量默认取 **no**；
3. `no` 使 configure 用 `AC_LIBOBJ([malloc])` 把 `malloc` 替换成 gnulib 的
   `rpl_malloc`，但源码未含该实现 → 链接报 undefined symbol（`AC_FUNC_REALLOC`
   同理产生 `rpl_realloc`）。

## Recommended Solution

**主方案：configure 显式传缓存变量覆盖误判。**

musl/glibc 的 `malloc(0)` 都返回可 free 的非 NULL 指针，置 yes 与目标平台实际
行为一致。一条 configure 参数解决，零补丁、零源码改动。

```python
# conanfile.py AutotoolsToolchain.configure_args 中
ac_cv_func_malloc_0_nonnull=yes
ac_cv_func_realloc_0_nonnull=yes
```

**回退方案**：若缓存变量注入不可行，对链接报错的 `rpl_malloc`/`rpl_realloc`
提供等价实现（包一层 malloc/realloc）或 patch `configure.ac` 移除
`AC_FUNC_MALLOC`——改动面大，不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **speech-dispatcher/0.12.1** | 主验证（本 PR） | ✅ 覆盖前 daemon 链接报 `undefined symbol: rpl_malloc`；传 `ac_cv_func_malloc_0_nonnull=yes`+`ac_cv_func_realloc_0_nonnull=yes` 后链接成功，conan create 通过 |

## 测试覆盖边界

- 缓存变量是 **configure 阶段**的探测值覆盖，不影响库行为（malloc(0) 本就正常）；
- 声明通过率时：以 conan create 全流程（daemon 链接成功 + test_package R34）为实证；
  speech-dispatcher 上游测试按 rule 1.2 平台限制声明（src/tests testsuite 需运行中的
  daemon + D-Bus + 声音设备，且链接 test 二进制时缺 gettext 符号——OHOS libintl 空 stub）。
