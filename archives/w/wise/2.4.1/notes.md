# wise 2.4.1 适配笔记

## 编译环境
- 构建系统: makefile（上游手写递归 makefile，无 configure；顶层入口 `src/makefile`）
- 编译日期: 2026-09-23
- 编译器: clang / clang++（`/data/service/hnp/bin/clang`，目标 aarch64-unknown-linux-ohos）
- 目标平台: OpenHarmony / HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`）
- 依赖: glib/2.88.3.1（Conan 制品仓 ohpcd，shared）
- 状态: published

## 编译步骤

上游约定（README/INSTALL）：`cd src && make all`，产物落在 `src/bin`，无 install 目标。
配方 `build()` 实际执行：

```bash
cd <source_folder>/src
make CC=clang CFLAGS="<下表 flags>" \
     GLIB_CFLAGS="-I<glib>/include/glib-2.0 -I<glib>/lib/glib-2.0/include" \
     GLIB_LIBS="-L<glib>/lib -lglib-2.0" -j1 realall
make bin        # 收集 11 个程序到 src/bin
# 层 1 上游测试套件
cd <source_folder>/src/test
perl testman.pl -cf ../wisecfg < short.test > upstream-test.log 2>&1
```

`realall` 依次构建 base（libwisebase.a）→ HMMer2（libhmmer.a）→ dynlibsrc
（libdyna.a / libdyna_glib.a）→ external（libmott.a）→ socket → dnaindex →
network → models（各程序 + libmodel.a），完成后 `bin` 目标复制 11 个可执行文件。

配方使用的编译/链接 flags：

| flag | 用途 |
|------|------|
| `-c -O2 -DUNIX -pthread` | 上游各子 makefile 的公共项（命令行传入统一覆盖） |
| `-fcommon` | 2007 年代码依赖 tentative definition 合并；clang 15 默认 `-fno-common` 会报 multiple definition |
| `-fsigned-char` | **关键**：OHOS/AArch64 上 `char` 默认无符号，上游 `char c = fgetc()` 与 `EOF(-1)` 比较恒假 |
| `-Wno-error=int-conversion` | 上游 `void*` → `char` 赋值（motifmatrix.c 等），与 Debian wise 2.4.1-25 起处理一致 |
| `$(GLIB_CFLAGS)` / `$(GLIB_LIBS)` | 由补丁 0001 引入，配方注入 Conan glib 包路径 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sh: glib-config: not found`，链接缺 `-lglib-2.0` | 上游用 glib 1.2 时代的 `glib-config` 工具，现代系统已无 | 补丁 0001：9 个 makefile 的 `` `glib-config --cflags/--libs` `` 改为 `$(GLIB_CFLAGS)`/`$(GLIB_LIBS)`，配方传 Conan glib 路径 |
| 2 | `make bin` 失败（`csh: not found`） | 顶级 makefile 的 bin 目标执行 `csh welcome.csh`（仅打印欢迎信息） | 补丁 0002：改为 `@echo` 跳过，不引入 csh 依赖 |
| 3 | `error: static declaration of 'getline' follows non-static declaration`（HMMer2/sqio.c，20+ 处） | HMMer2 自带静态 `getline(struct ReadSeqVars *)`，与 POSIX `getline()` 同名 | 补丁 0003：把该文件 34 处 `getline` 重命名为 `wise2_getline` |
| 4 | `ld.lld: error: undefined symbol: isnumber`（genewise/estwise/genewisedb/estwisedb） | `isnumber()` 是 BSD 专有接口，musl 未提供 | 补丁 0004：`src/models/phasemodel.c` 改用 `isdigit((unsigned char)…)` |
| 5 | `error: incompatible pointer to integer conversion … (aka 'int') -Wint-conversion`（compressed_protein_index） | 上游遗留 `return NULL;` 出现在 `boolean` 返回类型函数中 | `-Wno-error=int-conversion`（不改源码，与 Debian wise 处理一致） |
| 6 | 链接 `multiple definition of …` | clang 15 默认 `-fno-common`，而上游依赖 tentative definition 合并 | `-fcommon` |
| 7 | **上游测试仅 4/12 通过**：promoterwise `Length = 798`（应为 797）、basic-cdna 坐标整体 +1 并 SIGSEGV | OHOS/AArch64 上 `char` 默认**无符号**，`dynlibsrc/sequence.c` 的 `char c = fgetc(ifp); if (c == EOF …)` 恒假 → EOF 被当作一个碱基写入序列（长度 +1、坐标偏移），并破坏后续解析 | 加 `-fsigned-char` 后 **12/12 全部通过** |
| 8 | 解包后 `make` 调用不存在的 `dyc` 重生成 `.c` | 以不保留时间戳的方式复制源码（`cp -r`），`.dy` 被判为比 `.c` 新 | 解包/拷贝必须保留 mtime（tar 解包本身保留） |
| 9 | `init-build` 后源码树被破坏（顶层只剩 HMMer2 文件） | `init_build.py` 的 `_promote_nested_source`（F068）`_BUILD_MARKERS` 只含大写 `Makefile`；wise2 唯一的大写 `Makefile` 在 `src/HMMer2/`，被误提升到顶层 | 按原 tarball 重建 `.work`；工具侧应对 makefile 型项目增加小写 `makefile` 识别 |
| 10 | `clang -c …` 以非 0 码退出但**无任何诊断输出**（W3 本地 CI 下必现；同一目录手工执行同一命令却成功） | OHOS worker 上编译器/链接器输出若走管道会被静默丢弃，命令被判为失败 | 配方把每个构建步骤的输出重定向到日志文件（`_run_logged()`），失败时再将日志末尾回显到 conan 输出，既规避该现象又保留可诊断性 |

## 源码修改

补丁共 11 个（`patches/`，按文件生成、按序应用）：

| 补丁（按序应用） | 涉及文件 | 内容 |
|------|----------|------|
| `0001-src-HMMer2-sqio.c.patch` | `src/HMMer2/sqio.c` | 静态 `getline()` → `wise2_getline()`（34 处），消除与 POSIX `getline()` 的冲突 |
| `0002-src-models-phasemodel.c.patch` | `src/models/phasemodel.c` | `isnumber(line[0])` → `isdigit((unsigned char)line[0])` |
| `0003-src-makefile.patch` | `src/makefile` | glib 依赖改由配方注入；`csh welcome.csh` → `@echo` |
| `0004-src-corba-makefile.patch` | `src/corba/makefile` | glib 依赖改由配方注入 |
| `0005-src-dnaindex-makefile.patch` | `src/dnaindex/makefile` | 同上 |
| `0006-src-dnaindex-assembly-makefile.patch` | `src/dnaindex/assembly/makefile` | 同上 |
| `0007-src-dynlibsrc-makefile.patch` | `src/dynlibsrc/makefile` | 同上 |
| `0008-src-models-makefile.patch` | `src/models/makefile` | 同上 |
| `0009-src-network-makefile.patch` | `src/network/makefile` | 同上 |
| `0010-src-other_programs-makefile.patch` | `src/other_programs/makefile` | 同上 |
| `0011-src-snp-makefile.patch` | `src/snp/makefile` | 同上 |

> 「glib 依赖改由配方注入」= 把这 9 个 makefile 中 glib 1.2 时代的
> `` `glib-config --cflags` `` / `` `glib-config --libs` `` 替换为
> `$(GLIB_CFLAGS)` / `$(GLIB_LIBS)`，由配方从 Conan glib 包目录计算后经
> make 命令行传入（make 命令行变量自动传递给递归子 make）。

补丁生成后经自校验：把 11 个补丁按序 `patch -p1` 应用到原始 tarball 解压树，
结果与开发工作树**逐字节一致**（仅多一个工具产生的 `.patch-ai-review.txt` 元文件）。

> 关于 `-fsigned-char` 采用编译选项而非改源码：该无符号 char 问题散布在
> `dynlibsrc/sequence.c` 等多处 `char` / `EOF` 比较中（本次统计 11 处），
> 全局 `-fsigned-char` 一次性覆盖全部路径（含测试未覆盖的代码），
> 且恢复该代码在 x86 上的原始语义，不产生 `.c` 与 `.dy` 的额外分叉。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.88.3.1 | shared；上游只用到 glib2 仍提供的 `g_hash_table_*` / `g_tree_*` / `g_string_chunk_*` 等接口 |

## 验证结果

### 层 1：上游官方测试套件（build() 内执行）

```
cd src/test && perl testman.pl -cf ../wisecfg < short.test
→ Tests passed，test.results 为空（12/12）
```

| 用例 | 结果 |
|------|------|
| promoterwise | Passed |
| basic-cdna（estwise） | Passed |
| basic-genomic（genewise） | Passed |
| hmm-binary-cdna（estwise + 二进制 HMM） | Passed |
| hmm-wrong-dna（genewise，无匹配） | Passed |
| hmm-wrong-dna-est（estwise，无匹配） | Passed |
| hmm-ascii-genomic（genewise + ASCII HMM） | Passed |
| genewise-db（genewisedb HMM vs DNA 库） | Passed |
| genewise-db-lite（GWLITE 算法） | Passed |
| estwise-db（estwisedb HMM vs DNA 库） | Passed |
| pswdb（蛋白库 Smith-Waterman 搜索） | Passed |
| genewisedb-pfam-mode（Pfam 模式） | Passed |

上游测试通过率：**12/12 = 100%**（修复前 4/12，唯一差异是 `-fsigned-char`）。

### 层 2：鸿蒙特有测试（test_package，7 个完整端到端消费者用例）

> 2026-09-24 按 PR 评审 rule12 意见修订：原实现按「断言集合」计 1 项被判不合格
> （规则要求鸿蒙特有测试**至少有一个完整消费者用例，纯断言不算**）。
> 现重构为 7 个具名用例，每个都是完整端到端流程：
> 「消费者构造输入 → 真实执行包内安装的程序 → 程序读取包导出的 `WISECONFIGDIR`
> 运行期数据 → 产出真实比对结果 → 校验结果内容」，任一环节失败即该用例 FAIL。

| 用例 | 端到端流程与校验要点 |
|------|----------|
| HC-1 消费链路入口 | 11 个程序经 PATH 可定位；包导出 `WISECONFIGDIR` 且含 BLOSUM62.bla / codon.table / gene.stat / human.gf；11 个 `-version` 真实执行并报告 `wise2-4-1` |
| HC-2 `genewise -quiet short.pep short.dna` | 含 `roa1_drome` / `HSHNCPA1`；`Comp Matrix: BLOSUM62.bla`、`Codon Table: codon.table`、`Gene Parameter file: gene.stat` 均加载成功；含保守肽段 `DYDPVDKVVLQKQHQLNGK`；以 `//` 正常结束 |
| HC-3 `estwise -quiet short.pep short.dna` | 含保守肽段并以 `//` 正常结束 |
| HC-4 `dnal -quiet short.dna short.dna` | 自比对得分 `Score 2065`（确定性，与上游 `test/basic_cdna` 基线一致） |
| HC-5 `psw -quiet road.pep short.pep` | 含 rrm 保守肽段并以 `//` 正常结束 |
| HC-6 `dba -quiet short.dna short.dna` | `score = 695.64`，100% 覆盖、判定 `MATCH_D` |
| HC-7 `promoterwise -quiet short.dna short.dna` | 走完 `Search....done`，命中 `HSHNCPA1`、`Length = 415`（short.dna 真实长度）、含 `Sbjct:` 比对区段 |

新增测试通过率：**7/7 用例通过**（用例内合计 40+ 条断言）。

### 本机原生执行

11 个程序在 OHOS aarch64 上可直接运行（`-version` 均报告 `wise2-4-1`），
比对结果与上游参考输出一致。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/dba` | database alignment |
| `bin/dnal` | DNA × DNA 比对 |
| `bin/estwise` | EST / cDNA × 蛋白比对 |
| `bin/estwisedb` | estwise 的库搜索版本 |
| `bin/genewise` | 蛋白 × 基因组基因结构预测（核心工具） |
| `bin/genewisedb` | genewise 的库搜索版本 |
| `bin/promoterwise` | 启动子区比对 |
| `bin/psw` | 蛋白 Smith-Waterman 比对 |
| `bin/pswdb` | 蛋白库 Smith-Waterman 搜索 |
| `bin/scanwise` | scanwise 客户端 |
| `bin/scanwise_server` | scanwise 服务端 |
| `share/wise/wisecfg/` | 29 个运行期数据文件：BLOSUM62.bla、codon.table、human.gf、gene.stat 等 |

## 注意事项

1. **`-fsigned-char` 不可去掉**。去掉后上游测试退化为 4/12，且 genewise / estwise 在
   部分输入上会段错误。该问题在 AArch64 上必然出现（`char` 默认无符号）。
2. **运行期需要 `WISECONFIGDIR`**。genewise / genewisedb / estwise / psw / pswdb 等
   需要 `BLOSUM62.bla`、`codon.table`、`human.gf`、`gene.stat`；包已安装到
   `share/wise/wisecfg` 并通过 `package_info()` 的 `runenv_info` 导出
   `WISECONFIGDIR`（Conan 消费者使用 `conanrun` 环境可自动获得）。
   非 Conan 场景需手动指定：`export WISECONFIGDIR=<prefix>/share/wise/wisecfg`。
3. 上游 `make bin` 的清单为 11 个程序；`models/` 还会构建 `genomewise`、`sywise`、
   `pseudowise`，但它们不在上游 `make bin` 安装清单内，本包与上游保持一致，未收录。
4. 构建固定 `-j1`（R9）：递归 makefile 在 HMDFS 上并发会触发 jobserver fifo 问题。
5. 上游源码中 `.c` 与 `.dy` 并存（`.c` 由 dynamite 编译器预生成）。
   解包必须保留时间戳，否则 make 会尝试用 `dyc` 重新生成，而本包不构建 `dyc`。
6. 源码 tarball 采用 Debian 源码池镜像（上游 EBI 站点已下线），sha256 已与
   `wise_2.4.1-28.dsc` 的 Checksums-Sha256 交叉校验一致。
---

**编译结束**: 2026-09-23 23:09
**最终状态**: published

---

### 对话 #1 — 适配过程记录

- **起点**：上游 EBI 站点已下线，源码取自 Debian 源码池镜像（sha256 与
  `wise_2.4.1-28.dsc` 交叉校验一致）。
- **探索编译**：上游为手写递归 makefile（无 configure），按 README 的
  `cd src && make all` 路线在 OHOS aarch64 上交叉编译；依次解决
  `glib-config` 缺失、`csh` 依赖、HMMer2 局部 `getline()` 重名、
  BSD 专有 `isnumber()`、clang 15 默认 `-fno-common` 等移植点。
- **关键发现**：上游测试套件一开始只有 4/12 通过，且失败呈现「DNA 坐标整体 +1、
  部分组合段错误」的系统性特征；定位到 AArch64 上 `char` 默认无符号使
  `char c = fgetc(); c == EOF` 恒假（EOF 被当作一个碱基写入序列），
  加入 `-fsigned-char` 后 12/12 全部通过。
- **提交前验证**：`conan create` 通过；随后跑 W3 本地 CI 时又遇到「编译器输出
  经管道被静默丢弃、命令判为失败」的 worker 现象，配方改为把每步输出重定向到
  日志文件（`_run_logged()`）后 W3 全程通过（L0 pass / L1 pass / L5 pass）。
