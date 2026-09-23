# automake 生成规则的并行 install 目录竞态（install-sh 对 EEXIST 直接报错）——install 阶段必须 -j1

> Draft: DRAFT-PARALLEL-INSTALL-INSTALL-SH-EEXIST-RACE
> Stem: `DRAFT-parallel-install-install-sh-eexist-race` — pairs with the same-stem `.kv`
> 来源：libjpeg6b 6b2（automake 1.11.1 / autoconf 2.65 谱系），2026-09-15
> 正式 E 编号由知识库主编确认，本稿不预占编号；库名仅作案例，标题按问题类命名。
> **与 E999-draft-B839 的关系**：同一问题类（并行 install 目录创建竞态）的**第二实例**，
> 子机理不同——本例命中于 automake 生成的规则，推翻 E999"autotools 生成规则基本免疫"
> 的边界（autoconf ≤2.65 使 MKDIR_P 回退 install-sh 时免疫失效）。处置建议：主编在
> E999 晋级评审时将本稿并作同条目双实例证据，二者不应长期作为两条独立知识并存。

## 基本信息

- **ID**: DRAFT-PARALLEL-INSTALL-INSTALL-SH-EEXIST-RACE
- **严重度**: 2
- **类别**: autotools, automake, make, parallel-install, install-sh, HMDFS, OHOS
- **触发工具**: make | automake | install-sh | mkinstalldirs | conan
- **阶段**: installation

## 错误特征

```text
mkdir: '<DESTDIR>/include': File exists
make[1]: *** [Makefile:1065: install-data-local] Error 1
make[1]: *** Waiting for unfinished jobs....
make: *** [Makefile:944: install-am] Error 2
（伴生信号、非致命根因：make: jobserver mkfifo: ...: Operation not permitted）
```

## 可复现问题

automake ≤1.11 生成 Makefile.in 的 install 阶段存在**双重建目录**结构：

- `install-data-local`（用 `mkinstalldirs` → `install-sh -d`）为安装配置头先建 `$(includedir)`；
- `install-includeHEADERS`（用 `$(MKDIR_P)`；autoconf ≤2.65 在本设备探测 `mkdir -p`
  失败时回退为 `install-sh -c -d`）为装头文件也先建 `$(includedir)`。

两者是相互独立的安装目标。`install-sh` 建目录语义是 `test -d || mkdir`，且对
`mkdir` 的 EEXIST **直接报错退出**（不幂等，`mkdir -p` 则容忍已存在）。
`make install -jN (N>1)` 下两目标并发，后到者撞上"test -d 已过、mkdir 未落"的
窗口即报 `File exists` → `install-data-local Error 1` → `install-am Error 2`，
整个 install 失败。串行 `-j1` 时后者的 `test -d` 命中即跳过，从不报错。

HMDFS 背景条件：平台拒绝 jobserver mkfifo（E074 族），但这只破坏**跨 make 实例**
的令牌传递；单实例内 `-j` 并发照常发生（日志 `Waiting for unfinished jobs....`
可证并行确实发生）。因此 E074 的 `-j1` 建议在本场景是必要非充分——FIFO 限制
不是本竞态的根因，竞态也不是 FIFO 限制的表现，二者在 install 阶段并存。

## 根因分析

因果机理链（工具实现证据 → 触发命令 → 失败点 → 归类）：

1. 工具实现：automake 1.11 安装目标双建 `$(includedir)`；install-sh `test -d || mkdir`
   且 EEXIST 即错（实现证据：Makefile.in:1065/857 + install-sh mkdir 分支）。
2. 触发：`make install -j20`（CI 默认并行度）。
3. 失败点：`mkdir: '.../include': File exists` → `install-data-local Error 1` →
   `install-am Error 2` → Conan `package()` 抛 `ConanException: Error 2`。
4. 归类：**构建系统语义**（安装目标并行语义 × install-sh 非幂等建目录 × 平台
   MKDIR_P 探测回退），非上游代码缺陷、非库内私有 quirk。

## 推荐方案

**方法**: serial-install-j1

1. automake ≤1.11 / autoconf ≤2.65 谱系老包，make 的 build/check/install 全部显式
   `-j1`（Conan 配方：`autotools.make(args=["-j1"])`、
   `autotools.make(target="check", args=["-j1"])`、`autotools.install(args=["-j1"])`）。
2. 风险谱系判定：`grep -n "install-data-local" Makefile.in` 且
   `grep -n "MKDIR_P" Makefile.in` 同時命中建目录者即风险谱系。
3. 部分缓解（非全覆盖）：`make install MKDIR_P="mkdir -p"` 可把
   install-includeHEADERS 半边换成幂等 mkdir -p；但 install-data-local 走
   mkinstalldirs 的半边不受覆盖控制——`-j1` 是唯一全覆盖解。

## 回退方案（诚实权衡）

预建目录法：install 前先 `mkdir -p <DESTDIR>/{include,lib,share/man/man1}`。
只收窄竞态窗口、掩盖症状而非修复规则语义；对规则自建的更深层子目录仍可能漏建。
仅作无法改 `-j1` 场景的退路，不作为推荐方案替代。

## 反模式（forbid）

| 模式 | 原因 | 后果 |
|---|---|---|
| `make install -jN (N>1)` / `autotools.install()` 不带 -j1 | 竞态在 -j>1 下存在真实概率窗口 | install 随机崩溃，错误指向 install-data-local，易误诊为上游 bug 或磁盘/权限问题 |
| `make -k install` / 忽略 install Error 继续打包 | 违反 P-BUILD-001（平台限制必须降级而非绕过） | 头文件/库部分缺失的残缺包进入制品，问题后移到消费端 |

## 验证（自包含设备探针，不依赖任何 run 日志）

```sh
# 1) 背景条件：平台拒绝 FIFO（E074 族）
mkfifo /tmp/probe_fifo 2>&1; rm -f /tmp/probe_fifo   # 期望 Operation not permitted

# 2) 定向复现 install-sh "test -d || mkdir" 竞态语义（与具体库无关）
D=/tmp/probe_inst_race; rm -rf "$D"
for i in $(seq 1 20); do
  ( sh -c "test -d $D || mkdir $D" & sh -c "test -d $D || mkdir $D" & wait ) 2>&1 \
    | grep -q "File exists" && { echo "RACE reproduced at iter $i"; break; }
  rm -rf "$D"
done   # 期望：20 轮内出现 RACE reproduced

# 3) 真实触发路径：任一 automake≤1.11 谱系包
#    make install DESTDIR=... -j20 → "install-data-local] Error 1" + "File exists"
#    同路径 -j1 复跑 → PASS
```

## 挂钩与泛化

- `principles`: P-BUILD-001（平台限制必须降级而非绕过）、P-FS-001（HMDFS 不支持
  FIFO，替代方案）。
- `similar_to`: E074（make -j/FIFO 族——本条补全其 install 阶段机理）、
  E011（HMDFS 权限族）。
- `affected_scope`（泛化句式）：**任何**携带 automake ≤1.11 生成 Makefile.in（或
  autoconf ≤2.65 且 MKDIR_P 回退 install-sh）的 autotools 项目，在 -j>1 下执行
  `make install`。

## 与既有条目的差异（去重声明）

- **E999-draft-B839（最相近条目）**：手搓递归 Makefile install 并行竞态（prover9），
  同问题类（并行 install 目录创建竞态，`File exists` + `Error 1` + `Waiting for
  unfinished jobs`，-j1 全绿）。逐项差异：①触发面——E999 为无依赖排序的手搓递归
  Makefile，本条为 automake 1.11 **生成**规则的双建目录目标；②机理——E999 为裸
  `mkdir`（无 -p）非幂等，本条为 install-sh `test -d || mkdir` EEXIST 即错 +
  autoconf ≤2.65 平台探测失败致 `MKDIR_P` 回退 install-sh（平台语义增量）；③
  E999 断言"automake 生成的 install 通常带 mkinstalldirs/mkdir -p 与串行依赖，
  autotools 软件很少见到该竞态"——本例构成其反例，边界需修正。本条价值：为该类
  提供 L2 晋级所需的第二实例 + automake 谱系机理补全。建议主编合并而非长期并存。
- E074/E525（make -j/FIFO 族）：覆盖"jobserver FIFO 被拒 → make -j 卡住/报错 →
  用 -j1"，error_signature 不含 `mkdir: File exists`/`install-data-local Error 1`；
  且未解释"FIFO 被拒后单实例内并发仍发生并击穿 install 规则"。同族互补非重复。
- E571-draft-BED8：同盯 install-data-local，但属"缺 DESTDIR/srcdir 前缀装错位置"
  类，与本条竞态类互斥不重叠。
- E011（umask 077）：configure 期权限问题，阶段与机理均不同。
- 全库检索（graph 544 条 + drafts + 经验仓）无 automake 生成规则并行 install 竞态
  的条目（检索命令与命中清单见 curation/curation-report.md）。

## 关键词

parallel install, install-sh, EEXIST, File exists, install-data-local,
install-includeHEADERS, MKDIR_P, mkinstalldirs, automake 1.11, autoconf 2.65,
-j1, jobserver, mkfifo, HMDFS, OHOS, autotools, DESTDIR, conan

## 案例与来源

- libjpeg6b 6b2（archives/l/libjpeg6b/6b2）：round-01 `make install -j20` 失败
  （真实失败日志），round-03 全程 `-j1` 后 PASS；对照案例 jpeg-10（autoconf 2.69，
  MKDIR_P=真 mkdir -p）不受影响。
