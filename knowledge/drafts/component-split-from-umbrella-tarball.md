# 从「伞形」上游源码包拆分单个组件成独立 Conan 包（klibc 家族 usr/&lt;prog&gt;）

> Draft: DRAFT-COMPONENT-SPLIT-FROM-UMBRELLA-TARBALL
> Stem: `component-split-from-umbrella-tarball` — pairs with the same-stem `.kv`
> 来源：klibc-dash/2.0.14 适配（2026-09-25）。同族待适配对象：`klibc-run-init`、`klibc-nfsmount`

## 基本信息

- **ID**: DRAFT-COMPONENT-SPLIT-FROM-UMBRELLA-TARBALL
- **严重度**: 1
- **类别**: packaging|build-system|portability|conan|structure
- **触发工具**: make|conan|cmake
- **阶段**: configuration|compilation|packaging

## 问题形态

发行版/镜像侧常按「组件」命名拆包（`klibc-dash`、`klibc-run-init`、`klibc-nfsmount`），
但上游只发布**一份伞形 tarball**。直接照搬整树构建会踩三件事：

1. **连带构建无关组件**：klibc 顶层 `Kbuild` 的 `all` =
   `scripts/basic + usr/klibc + usr/kinit + usr/dash + usr/utils + usr/gzip`；
2. **版本号无处可取**：`usr/dash/config.h` 里是历史快照值 `dash 0.5.7`，与 klibc `2.0.14` 不一致；
3. **边界互相踩**：仓库内已有同上游整包配方（`klibc/2.0.14` 用 patch 0004 **显式跳过 `usr/dash`**），
   组件包必须独立适配，且不能与整包重复/冲突。

## 六步做法（klibc-dash 实证）

| 步 | 做法 | klibc-dash 实例 |
|---|---|---|
| ① | 版本号取**父发行版本**（读 `<src>/usr/klibc/version`），并在 README/notes 说明与组件自身版本串的区别 | `2.0.14`（而非 dash 的 0.5.7） |
| ② | 用 patch **收窄顶层构建范围**的 `all` 目标，只保留本组件 + 其必需的同树依赖 | patch 0004 → `scripts/basic + usr/klibc + usr/dash` |
| ③ | 组件与同树依赖**静态链接**成自包含产物，不因此引入第三方 `requires`（也就不需要为同树 libc 单独发包） | `bin/sh`（静态，无 PT_INTERP） |
| ④ | 产物形态决定配方声明：可执行文件 → `package_type="application"` + 软件级 `commands.json`（R38） + `cpp_info.bindirs=["bin"]` | `archives/k/klibc-dash/commands.json` |
| ⑤ | 上游无 `make install`（无 GNU install，E098）时用 Conan `copy` 手动打包 | `copy(static/sh → bin/sh)` + 签名 |
| ⑥ | **上游测试按组件口径如实申报**：组件目录无测试要附清点证据；把同树唯一自动化入口真实执行、逐项留档；不得用 test_package 冒充上游测试统计（R51） | `make test` → 39 用例 39/39；`usr/dash` 无测试已取证 |

## 测试口径的两个易错点

- **shared 形态**：上游用例常有 static/shared 双形态（klibc 为 39×2=78 二进制）。klibc 的
  shared 形态以共享库本身作解释器（`PT_INTERP=/lib/klibc-<hash>.so`），而 OHOS `/lib -> /system/lib`
  为只读系统分区 → shared 形态结构性不可执行。**可执行用例数应按 static 39 个申报**（附证据），
  而不是含糊地写「78 个测试」。
- **非判定型样例**：`testrand48` 硬编码 `return 1`（只打印 rand48 值供人工比对、无断言）。
  这类样例应作为「上游测试用例修改说明」单独申报（改 `return 0` 以纳入退出码统计），
  而不是让它长期以「失败」出现在统计里。

## 验证与判据

- 清点：`tar tJf <tarball> | grep -E '^[^/]+/(usr|src)/'`；`grep -n 'all:' -A 12 <src>/Kbuild`
- 收窄有效性：应用 patch 后 `grep -n 'usr/dash' <src>/Kbuild` 只剩目标组件
- 组件无测试的证据：`ls <src>/usr/dash | grep -iE 'test|check'`（rc=1）+ 无 `tests/` 目录
- 关联：E098（无 GNU install）、E077（OHOS ELF 签名）、E002（/tmp 只读）、E265（上游测试口径）
