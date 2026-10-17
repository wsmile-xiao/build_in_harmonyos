# DRAFT-lcrq-0.4.1-hard-dependency-decomposition-w0 — W0 依赖检查发现"无条件硬链接依赖"时必须先拆出依赖库独立适配

> **Contributor**: gcw_6YxinkyD | **Status**: DRAFT | **Updated**: 2026-09-22
> **Severity**: high (3) | **Category**: conan / workflow / dependency-analysis
> **Audience**: 所有执行 W0 依赖检查的适配工程师

## 触发（trigger）

librecast/0.11.2 适配时 W0 依赖检查：上游 `src/Makefile.in:41` 无条件
`LIBS += -llcrq`。即使 configure 的 `AC_CHECK_LIB(lcrq, rq_init)` 探测失败，
Makefile 仍在链接阶段传入 `-llcrq`，导致 `ld` 报 `cannot find -llcrq`。

ohpcd 制品仓上只有 lcrq/0.3.1（API 不兼容），没有 lcrq/0.4.1。

## 症状（symptom）

```
librecast.so.0.6: cannot find -llcrq
collect2: error: ld returned 1 exit status
```

即使在 librecast 配方中尝试 `self.cpp_info.ignored_requires = ["lcrq"]`
或手动去掉 `-llcrq` 链接选项，链接仍失败——因为 `src/Makefile.in` 的
`LIBS` 变量被无条件赋值，不是 configure 探测驱动的可选链接。

## 机制（root cause）

部分 autotools 项目的 Makefile.in 将依赖库硬编码在 `LIBS` 变量中：

```makefile
# src/Makefile.in
LIBS += -llcrq -lsodium
```

这与 `AC_CHECK_LIB` 探测驱动的条件链接不同：
- 条件链接：`configure` 探测成功才 `HAVE_LCRQ=1`，Makefile 按条件拼接
- 无条件硬编码：无论 configure 结果如何，链接行始终包含 `-llcrq`

当此类依赖不在制品仓中时，**无法通过 ignored_requires 或链接选项剔除**——
必须将依赖库作为独立 Conan 包先行适配发布。

## 修复（resolution）

1. **W0 阶段识别**：在源码中 grep `LIBS +=.*-l` 和 `AC_CHECK_LIB`，对比哪些
   是无条件硬编码、哪些是条件探测。
2. **拆出依赖库独立适配**：lcrq/0.4.1 创建独立 worktree、独立分支
   `feat/lcrq-0.4.1`、独立 PR。lcrq 是纯 C 库（无外部依赖），适配难度低。
3. **主库配方声明 requires**：librecast 配方 `self.requires("lcrq/0.4.1")`，
   conan create 自动从制品仓拉取 lcrq 并注入 `-I`/`-L`/`-l`。
4. **依赖顺序**：先合 lcrq PR 发布制品，再合 librecast PR。

lcrq 真机构建结果：20 个上游测试全部通过（纯算法，无网络依赖）。

## 判定清单（hard vs soft dependency）

| 特征 | 软依赖（可条件编译） | 硬依赖（必须独立适配） |
|------|---------------------|----------------------|
| Makefile LIBS | 按 `@HAVE_LIB@` 条件拼接 | 无条件 `+= -lxxx` |
| configure | `AC_CHECK_LIB` 失败时 `--without-xxx` | 无 `--without` 选项 |
| 头文件 | `#ifdef HAVE_XXX_H` | `#include <xxx.h>` 无条件 |
| 制品仓 | 有兼容版本 | 无或版本不兼容 |

## 反模式（anti-patterns）

- ❌ 在主库配方中 `ignored_requires` 硬编码依赖——链接阶段仍报 cannot find -lxxx
- ❌ 修改上游 Makefile.in 去掉 `-lxxx` 链接——破坏构建语义，上游其他消费者
  依赖该链接行为
- ❌ 把依赖库源码 vendored 进主库——违反"一库一配方"原则，依赖版本无法独立更新

## 关联

- similar_to: W0 依赖检查流程（SKILL.md W0 章节）
- 实际案例：librecast/0.11.2 → lcrq/0.4.1（本 draft 来源）
