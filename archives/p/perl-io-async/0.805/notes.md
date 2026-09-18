# perl-io-async (IO::Async) 0.805 适配笔记

## 概述

IO::Async 是 Perl 的**事件驱动异步编程框架**（Loop / Notifier / Stream /
Timer / Handle / Process / Resolver 等），提供 future 化的异步 I/O 抽象。

- 上游：https://metacpan.org/pod/IO::Async
- 版本：0.805
- 构建系统：**Perl**（Build.PL / Module::Build，本配方不调用）
- 许可：Artistic-2.0
- 编译日期：2026-09-16
- 状态：built

## 内容（实测自 CPAN tarball）

| 项 | 数量 |
|---|---|
| `lib/**/*.pm` | **39** |
| `t/*.t` | **64** |
| `examples/` | 有 |

`lib/` 除 `IO::Async::*` 框架外，还内含 `Future/IO/Impl/IOAsync.pm`
（做为 Future::IO 的实现之一随本发行版分发）。

## 依赖：本批四包中最复杂的一个

`META.json` 声明的非核心依赖（**均需区分 requires / recommends**）：

| 模块 | 性质 | 本机可用 | 影响 |
|---|---|---|---|
| **`Future` >= 0.44** | **runtime requires** | ❌ **无** | **12 个 `lib/` 文件 `use Future`** → 27/39 模块无法加载 |
| **`Future::Utils` >= 0.18** | runtime requires | ❌ 无 | `IO::Async::Handle` 需要 |
| **`Struct::Dumb`** | runtime requires | ❌ 无 | 部分模块需要 |
| `IO::Socket::IP` | *recommends* | ❌ 无 | **可选**，缺失不致命 |

### 实测影响（决定性数据）

无 `Future` 时逐模块加载测试：

```
可加载: 12
失败:   27
```

失败者**全部**报 `Can't locate Future.pm in @INC`——即**环境依赖缺口**，
而**不是**打包缺陷。例如：

```
$ perl -Ilib -MIO::Async::Loop -e 1        → OK
$ perl -Ilib -MIO::Async::Notifier -e 1    → Can't locate Future.pm
```

> ⚠️ 关键区分：缺的是 **`requires`（硬依赖）而非 `recommends`**。
> 若只是 recommends 缺失，框架仍可正常使用；此处是硬依赖缺失，
> 故**框架实质性不可用**（仅 12/39 模块可加载）。

### 按仓内惯例**不声明** conan requires

实测量化：抽样 30 个既有 `perl-*` 配方，**仅 1 个**声明了 `self.requires("perl-...")`；
`perl-moose`（依赖极多）的配方里写的是：

```python
def requirements(self):
    # Perl XS module dependencies are handled at the Perl/system level,
    # not as Conan packages. See notes.md for dependency installation.
    pass
```

故本配方沿用同一做法：**在 `build()` 内探测**这些依赖、**显式输出缺口清单与
影响面**（R51），并在本文件与 `manifest.yaml` 记录，而不是把它们写成 conan
依赖（那些包当前也未发布到 ohpcd）。

## 上游测试

`t/` 下 **64** 个 `.t` 文件。**47 个**在 BEGIN 期 import 缺失的非核心测试依赖
（`Test::Metrics::Any` 被 5 个文件引用、`Test::Future::IO::Impl` 等），
**prove 会因收集失败而整体中断**：

```
Files=64, Tests=130 ... Result: FAIL   （55 个文件 Parse errors: No plan found in TAP output）
```

### 处置：`perl -c` 预检，仅跑可运行子集

配方先用 **`perl -c`（编译检查，不执行主体）**逐个预检每个 `.t`，
把报 `Can't locate` 的划为 blocked，只对可运行子集执行 `prove`，
并**显式输出排除理由**（R51，不静默跳过）：

| 类别 | 数量 |
|---|---|
| BEGIN 期 import 缺失（无法收集）| **47** |
| 可运行 | **17** |
| 其中通过 | **10** |
| 其中失败 | 7（均因 `Future` 缺失的运行时缺口，非本适配引入）|

> 若将来 `Future` / `Test::*` 依赖发布，预检会自动把它们纳入，
> **无需改配方**（自愈式设计）。

## 消费者测试（test_package）

`test_package/test_io_async.py`（经 perl 解释器驱动），断言全部基于实测：

| 组 | 断言 |
|---|---|
| **模块齐全** | 打包的 `.pm` 数**恰为 39**；含 `IO/Async/Loop.pm`、`IO/Async/Notifier.pm`、`Future/IO/Impl/IOAsync.pm` |
| **Future-free 子集真实加载** | `IO::Async::OS` / `Loop` / `Debug` / `Time` 逐个 `require` 成功 |
| 版本 | `$IO::Async::Loop::VERSION == "0.805"` |
| **真实 API 调用** | `IO::Async::Loop->new` 构造成功且返回对象类型正确 |
| **依赖缺口行为一致** | `IO::Async::Notifier` 报 `Can't locate Future.pm`（与实测一致）；若将来 Future 可用，则输出提示而**非误判失败** |

设计取向：与其假装框架"完全可用"，不如**精确验证打包完整性**（39 模块齐全、
可加载子集真能加载、缺口与预期完全一致）——这才是本包当前能给出的最强证明。

## 验证结果

```
conan create archives/p/perl-io-async/0.805 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0
```

| 项 | 实测结果 |
|---|---|
| `conan create` | **exit=0**，Package created |
| 依赖探测输出 | `non-core runtime dependency(-ies) unavailable: Future, Future::Utils, Struct::Dumb — of the 39 packaged modules only the subset not importing Future is loadable (12/39 measured)` |
| 测试排除 | `excluding 44 of 64 files whose BEGIN-time imports cannot be satisfied ... missing: Test::Future::IO::Impl, Test::Metrics::Any` |
| 上游 prove（可运行子集）| **有失败**：`# Tests were run but no plan was declared and done_testing() was not seen.` / `# Looks like your test exited with 2 after test #1.` 配方据此输出 `upstream prove reported failures in the runnable subset` |
| 消费者测试 | `perl-io-async (IO::Async 0.805) consumer API: PASS (39 modules packaged, 5 future-free samples load)` |

### 关于「可运行子集仍有失败」——如实说明

按文件逐个实测：**可运行 17 个中 10 通过、7 失败**（另有 47 个因 BEGIN 期
import 缺失而阻塞；配方内 `perl -c` 预检报 44 个，两者差异来自预检与直跑的判定
粒度不同，以配方输出为准）。

**7 个失败均源于同一环境缺口**：这些用例在用例体内用到了 `Future`（如
`IO::Async::Future` 相关路径），而非仅 BEGIN 期 import——故预检（只编译不执行）
无法提前筛出，运行到该断言才失败。

这属**依赖缺口导致的运行期失败**，**非本适配引入**；配方已把该事实显式输出
（`upstream prove reported failures in the runnable subset`），未做静默处理。
待 `Future` 等依赖发布后，这些用例应随之转绿。

## 注意事项

1. **必须区分 `requires` 与 `recommends`**——本包缺的是硬依赖 `Future`，
   框架因此实质性不可用（12/39 可加载）；
2. **不要直接 `prove -l t`**——47/64 文件会因收集失败而中断整个运行，
   须先用 `perl -c` 预检筛出可运行子集；
3. 按仓内 perl-* 惯例**不声明 conan requires**，依赖缺口在 notes/manifest
   记录 + 配方内探测输出（R51）；
4. `package()` 内断言 **39 个模块**——递归拷贝若写错会静默丢子目录。
