# DRAFT-ohos-perl-noncore-runtime-dep-requires-vs-recommends — Perl 非核心依赖须区分 requires/recommends

> Contributor: B2E5 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-perl-noncore-runtime-dep-requires-vs-recommends`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-ohos-upstream-tests-bare-import-unpublished-dep` | 在本轮 PR #10408（greenlet）| 上游**测试**文件裸 import 未发布依赖 → 套件不可收集 | 那条只讲**测试期**依赖；**本条讲运行时依赖的档位语义**（requires 缺失＝功能不可用 vs recommends 缺失＝降级可用），并给出**量化影响面**的方法。实测 `IO::Async` 命中 0 |
| `perl-carp` 等纯 Perl 包 | 已在 main | `prereqs` 仅核心模块，无外部依赖 | 那类不存在本问题；本条的适用面是**有非核心依赖**的 Perl 包 |

**全库查证**：`非核心依赖` / `runtime requires vs recommends` / `IO::Async` /
`IO-Async` 等关键词**命中 0**（`recommends` 有 9 处，但均非 Perl 依赖档位语境）。

## Scope（何时用）

**非核心依赖未随解释器分发**的 Perl 包适配。典型是 CPAN 生态的框架类包。

对照实测样本（IO-Async 0.805）：

| 模块 | 档位 | 缺失后果 |
|---|---|---|
| `Future` (>=0.44) | **runtime requires** | 12 个 `lib/` 文件 `use Future` → **27/39 模块无法加载** |
| `Future::Utils` (>=0.18) | runtime requires | `IO::Async::Handle` 需要 |
| `Struct::Dumb` | runtime requires | 部分模块需要 |
| `IO::Socket::IP` | ***recommends*** | **可选**，缺失不影响加载 |

## Symptom

```console
Can't locate Future.pm in @INC (you may need to install the Future module)
(@INC entries checked: .../lib .../site_perl/5.42.2 ...)
        at .../lib/IO/Async/Notifier.pm line 14.
```

实测逐模块加载结果（决定影响面）：

```
可加载: 12
失败:   27        ← 全部因 Can't locate Future.pm
```

## Root Cause

`META.json` 的 `prereqs` 分三档（`requires` / `recommends` / `suggests`）并分期
（`runtime` / `test` / `configure`）。语义差别很大：

- `requires` 缺失 → **功能不可用**（import 即失败）；
- `recommends` 缺失 → **降级但可用**。

**把二者混为一谈**（例如只数"缺了几个依赖"而不管档位），就会把"框架实质不可用"
误判为"少个可选功能"。

### 本仓惯例：不把 Perl 依赖写成 conan `requires`

实测抽样 30 个既有 `perl-*` 配方，**仅 1 个**声明了 `self.requires("perl-...")`。
`perl-moose`（依赖极多）的 `requirements()` 直接：

```python
def requirements(self):
    # Perl XS module dependencies are handled at the Perl/system level,
    # not as Conan packages. See notes.md for dependency installation.
    pass
```

→ 依赖缺口不能靠 `requires()` 表达，只能**探测 + 如实申报**（R51）。

## Recommended Solution

### 主方案（priority 1）— 探测 + 量化影响面 + 如实申报

在 `build()` 内：

1. **探测** `requires` 档模块是否可加载，列出缺失者；
2. **量化影响面**（如"39 个模块中 27 个无法加载"）——让评审一眼看出是
   "框架实质不可用"还是"少个可选功能"；
3. **说明处置方向**（Perl 层面依赖，需适配并发布后方达完整功能），并在
   `notes.md` / `manifest.yaml` 按 **required / optional / rejected** 三档归类记录。

**测试侧另有一层**：`prove` 遇到 BEGIN 期 import 失败会**整体中断**，故须先用
`perl -c` 逐个预检筛出可运行子集，再对子集跑，并显式输出被排除文件数与缺失依赖。

**设计成自愈式**：探测通过即自动纳入，无需改配方。

### 回退方案（priority 2）— 适配并发布 Perl 依赖后在 conan 层表达

若确需可解析的依赖图，须先把这些 CPAN 发行版逐一适配并发布，再以 `requires()` 引入。
代价：依赖链显著变长，且与仓内既有 `perl-*` 惯例不一致，需与维护者确认口径。

### 禁止做法

- ❌ 不区分 `requires`/`recommends` 就统计依赖影响面——会误判严重程度；
- ❌ 因 `Can't locate X.pm` 去改本包源码、注释掉 `use`、或伪造 `.pm` 桩
  ——缺失的是**外部模块**，伪造桩与真模块行为不一致时会给出**虚假通过**；
- ❌ 静默跳过全部测试——违反 R51，使"依赖缺失"与"功能正常"无差别；
- ❌ **只按报错文本分支、不检查退出码**——见下。

### 只按报错文本分支 = 假成功（review 实测抓出）

探测"某依赖是否已可用"时，若**只用报错文本**决定分支而不检查 `rc`，任何**其它原因**
的失败都会落进"依赖已可用"的路径。实测：把探测目标换成一个**根本不存在的模块**，
旧代码仍打印：

```
NOTE: Future appears to be available now — the module loaded; ...
perl-io-async (IO::Async 0.805) consumer API: PASS (39 modules packaged, ...)
exit=0
```

——测试断言的事实与真相**相反**，恰好掩盖了它本该检出的回归；而"依赖后来可用了"
正是该分支宣称要覆盖的自愈场景，也就是说这个缺陷**恰在最需要它工作时失效**。

**正确顺序**：

1. **先判 `rc`**；
2. `rc == 0` → 才谈"依赖已可用"（此时还须确认真的加载成功，而非空跑退出 0）；
3. `rc != 0` → 再看报错文本是否**正是**所缺依赖：
   - 是 → 按预期的依赖缺口处置（如实记录，非缺陷）；
   - 否 → **必须失败**（可能是打包回归/语法错误，不能被当成"依赖已具备"放行）。

## 实测证据（2026-09-16，perl-io-async 0.805 适配）

| 项 | 结果 |
|---|---|
| `Future` 档位 | **runtime requires**（>=0.44），12 个 `lib/` 文件 `use Future` |
| 逐模块加载 | **12 可加载 / 27 失败**（失败全为 `Can't locate Future.pm`）|
| `IO::Socket::IP` | 仅 *recommends*，缺失不影响加载 |
| 上游测试 | 64 个 `.t`；**47** 个 BEGIN 期 import 缺失（`Test::Metrics::Any` 等）不可收集 |
| 处置 | 配方探测并输出缺口 + 影响面；MANIFEST 标 `upstream_test_in_build: false` |
| 修复后 | `conan create` exit=0、consumer API PASS |

## 测试覆盖边界

本条处理"**Perl 运行时依赖档位与影响面**"。区分相邻情形：

- 上游**测试**文件裸 import 未发布依赖 → `DRAFT-ohos-upstream-tests-bare-import-unpublished-dep`；
- 依赖库**符号**未实现 → `DRAFT-ohos-dependency-library-missing-own-symbols`；
- 纯 Perl 包无外部依赖（`perl-carp`）→ 不存在本问题。

## 关联条目

- 相似：`DRAFT-ohos-upstream-tests-bare-import-unpublished-dep`（测试期同类）
- 差异：见上方差异化定位表
