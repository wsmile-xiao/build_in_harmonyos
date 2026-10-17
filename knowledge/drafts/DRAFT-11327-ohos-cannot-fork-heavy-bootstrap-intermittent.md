# 受限 CI worker 上的间歇性 `can't fork - try again`：先判环境资源，再避免高开销自举步骤

- **草稿 ID**: DRAFT-11327-ohos-cannot-fork-heavy-bootstrap-intermittent
- **来源**: rnnoise 0.2 HarmonyOS PC 适配（同一提交在不同 worker 上一次通过、一次 `can't fork`）
- **分类**: ci-infra / autotools-bootstrap / resource-limits / diagnosis
- **状态**: 本地草稿（已挂 PR #11327，路径 B 知识库扩展申请中）

## 问题 / 错误签名

- `.../autom3efab95d532f9/p/bin/aclocal[4]: can't fork - try again` → `autoreconf: error: .../aclocal failed with exit status: 1`（CI build #51238）
- `/system/bin/sh: .../conanautotoolstoolchain.sh[13]: can't fork - try again` → `rnnoise/0.2: Error in build() method ... autoreconf -fi`（CI build #51345）
- 同一段日志里 CI 自身脚本也在报资源错误：`junk_check.sh: line 200: /data/service/hnp/bin/grep: Out of memory`、`/usr/bin/cut: Out of memory`、`knowledge_check.sh: fork: Out of memory`
- 对照：**同一 commit 的另一次构建（#51220，worker CI-020）在完全相同的 `autoreconf -fi` 上成功**并推进到编译阶段——这是"环境资源"而非"配方缺陷"的判据。

## 根因

1. **`can't fork` = 进程创建失败（EAGAIN）**：worker 处于 fd/内存/进程数压力下，`fork()` 被拒；`sh`、`aclocal`、`automake` 这类**高 fork 开销**的自举链路最先受害。
2. **症状间歇且与 worker 绑定**：同一提交在不同 worker / 不同时刻结果不同；失败点常在"第一个 fork 密集的步骤"，容易误判为配方 bug。
3. **连锁放大**：`autoreconf -fi` 会依次 fork `aclocal`/`autoconf`/`autoheader`/`libtoolize`/`automake`，任一环节失败即 `exit status 1`，错误信息只指向自举链，不暴露资源根因。

## 判定方法

- **必要判据**：同一 commit（同 SHA）在不同 worker 上结果不一致；或失败点落在 CI 自身脚本（非目标包）的 fork/内存报错上。
- **看日志旁证**：同一 log 段内出现 `Out of memory` / `fork: Out of memory` / `can't fork` 多处（含 CI 脚本），基本可判环境压力。
- **反例排除**：若失败信息是明确的编译错误（`fatal error: ... file not found`、`undefined reference`）且**可复现**，则不是本条目范畴。

## 修复策略（按优先级）

1. **移除自举步骤**：改用**自带预生成 `configure`/`Makefile.in` 的官方发行包**（release dist tarball），配方里仅在缺 `configure` 时才回退 `autoreconf`：

```python
_cfg = os.path.join(self.source_folder, "configure")
if not os.path.exists(_cfg):
    self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
```

2. **降低并发**：`autotools.make(args=["-j1"])`，避免与大内存链接竞争。
3. **必须自举时**：重试/换 worker（等待队列空闲），并在 `notes.md` 记录"间歇性环境失败 + 实测对照"，**不得伪造通过**。

## 适用范围

- 全部在共享/受限 worker 上执行 Autotools 自举（`autoreconf`/`aclocal`/`automake`/`libtoolize`）或高并发编译（大内存链接）的适配；
- 同型签名还包括 `fork: Out of memory`、`Resource temporarily unavailable`、`Bus error`（内存压力下）等**间歇性**基础设施失败；
- 也适用于"同一 SHA 重跑后通过"的所有排障场景：**先用同 SHA 对照判断是否环境问题，再决定是否改配方**。

## 边界 / 反例

- 官方**只提供 git 快照**（无 release 资产、无预生成 configure）时无法用策略 1 移除自举，只能降并发 + 重试，并如实记录；
- 本条目**不**为"跳过测试/伪造状态"提供任何借口：由资源导致的失败必须留下可复核的日志与对照证据。

## 实证

| 项目 | 内容 |
| --- | --- |
| 失败样本 | CI #51238（worker CI-011）`aclocal[4]: can't fork`；CI #51345（worker CI-032）`conanautotoolstoolchain.sh[13]: can't fork` |
| 对照样本 | CI #51220（worker CI-020）同 SHA 上 `autoreconf -fi` 正常通过 → 环境性 |
| 旁证 | 同批日志中 `grep`/`cut`/`knowledge_check.sh` 均报 `Out of memory` |
| 处置 | 配方改为"发行包自带 configure 时跳过 autoreconf"（rnnoise 0.2 dist tarball），`make -j1`；修复后 CI #52746 通过 |

## 关联

- PR：#11327（`feat/rnnoise-0.2`）
- 同批草稿：`DRAFT-11327-upstream-dist-drops-referenced-header-non-x86-path`（同库另一类问题）
- 既有相邻条目（区分点）：`gmime-release-tarball-native-run-probe`（选 release 包是**为省冗余自举**，非资源受限）；`swftools-autotools-hmdfs`（权限/安装层加固）