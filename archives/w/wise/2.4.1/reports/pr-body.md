- **三方库名称**：wise（EBI Wise2 / Dynamite 工具集）
- **上游版本**：2.4.1
- **上游仓库地址**：https://www.ebi.ac.uk/~birney/wise2/
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent 编译技能

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无单元测试框架 |
| 集成测试 | 12 | 来源：`src/test/short.test`（由 `src/test/testman.pl` 驱动，`make -C src test` 即 `cd src/test && perl testman.pl -cf ../wisecfg < short.test`）。每个用例真实运行构建出的 11 个程序之一，并用 `diff` 比对参考输出 `src/test/*.out`：promoterwise / basic-cdna / basic-genomic / hmm-binary-cdna / hmm-wrong-dna / hmm-wrong-dna-est / hmm-ascii-genomic / genewise-db / genewise-db-lite / estwise-db / pswdb / genewisedb-pfam-mode |
| 其他测试 | 0 | — |
| **合计** | **12** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 12 | 不变 | 12 个上游用例已完整集成进 `conanfile.py` 的 `build()`（`conan create` 时自动执行），未删改任何用例或参考输出 |
| 鸿蒙特有测试 | 7 | 新增 7 | `test_package/test.sh` 的 **7 个完整端到端消费者用例**（非纯断言）：每个用例都真实执行包内安装的程序、读取包导出的 `WISECONFIGDIR` 运行期数据、产出真实比对结果并校验内容——HC-1 消费链路入口（11 程序 PATH 定位 + 运行期数据 + `-version`）、HC-2 genewise 蛋白×基因组 DNA、HC-3 estwise 蛋白×cDNA、HC-4 dnal DNA×DNA（Score 2065）、HC-5 psw 蛋白×蛋白、HC-6 dba DNA×DNA（score 695.64 / 100% / MATCH_D）、HC-7 promoterwise 双 DNA 启动子预测（Search done + 命中 HSHNCPA1 + Length = 415 + Sbjct 区段）。实测 7/7 通过，用例内合计 40+ 条断言 |
| **合计** | **19** | **+7** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：4 个补丁只涉及构建文件与两处 C 源码移植点（makefile 的 glib 依赖写法、
> `csh` 调用、HMMer2 局部 `getline()` 重名、`isnumber()`），**未触碰**
> `src/test/short.test`、`src/test/testman.pl` 及任何 `src/test/*.out` 参考输出。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 说明：上游自带 `src/test/short.test` 的 **12 个**集成用例，适配未修改也未“补全”上游用例。
> 适配后新增的 **7 个**「鸿蒙特有测试」位于 `test_package/test.sh`，在 conanrun 环境内
> 真实执行安装后的二进制，且**每个都是完整端到端消费者用例**（不是纯断言集合）：
> HC-1 消费链路入口（11 程序 PATH 定位 + `WISECONFIGDIR` 运行期数据完整性 + 11 个 `-version`）、
> HC-2 genewise（蛋白×基因组）、HC-3 estwise（蛋白×cDNA）、HC-4 dnal（DNA×DNA）、
> HC-5 psw（蛋白×蛋白）、HC-6 dba（DNA×DNA 块比对）、HC-7 promoterwise（双 DNA 启动子预测）。
> 每个用例均由消费者构造 FASTA 输入 → 真实执行程序 → 程序读取包导出的 `WISECONFIGDIR`
> 数据 → 产出真实比对结果 → 校验结果内容，任一环节失败即该用例 FAIL。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：[12/12]（100%，`conan create` 的 `build()` 内执行 `perl testman.pl -cf ../wisecfg < short.test`，输出 `Tests passed` 且 `test.results` 为空）
- 新增测试用例通过率：[7/7]（100%，7 个完整端到端消费者用例全部通过，用例内合计 40+ 条断言）

## 补充说明

**关键适配点：AArch64 上 `char` 默认无符号导致的序列读取缺陷（本项目最大坑点）**

OHOS/AArch64 上 `char` 默认**无符号**，而上游 `dynlibsrc/sequence.c` 等处以
`char c = fgetc(ifp); if (c == EOF …)` 判断文件结束——无符号 `char` 使该比较恒假，
EOF 被当作一个碱基写入序列，表现为序列长度 +1、坐标整体偏移，并破坏后续解析
（部分组合直接段错误）。这解释了适配初期上游测试仅 4/12 通过：
`promoterwise` 报告 `Length = 798`（真实与参考均为 797），`basic-cdna` 的 CODON
坐标整体 +1 且进程 SIGSEGV。加入 `-fsigned-char` 后（不引入源码分叉），
上游测试由 4/12 提升到 **12/12**。

**补丁清单（11 个，`patches/`，按文件生成、按序应用）**

| 补丁（`patches/`，按序应用） | 内容 |
|------|------|
| `0001-src-HMMer2-sqio.c.patch` | HMMer2 `sqio.c` 自带静态 `getline()` 与 POSIX `getline()` 冲突（34 处），重命名为 `wise2_getline()` |
| `0002-src-models-phasemodel.c.patch` | `isnumber()` 为 BSD 专有接口（musl 无），改用 `isdigit((unsigned char)…)` |
| `0003-src-makefile.patch` | 顶层 makefile：glib 依赖改由配方注入；`bin` 目标不再执行 `csh welcome.csh`（仅打印欢迎语，OHOS 无 csh） |
| `0004`–`0011-src-*-makefile.patch`（8 个） | corba / dnaindex / dnaindex-assembly / dynlibsrc / models / network / other_programs / snp 的 makefile：`` `glib-config --cflags/--libs` ``（glib 1.2 时代工具，现代系统已无）改为 `$(GLIB_CFLAGS)` / `$(GLIB_LIBS)`，由配方注入 Conan glib 包路径 |

> 补丁经自校验：11 个补丁按序 `patch -p1` 应用到原始 tarball 解压树，结果与开发工作树逐字节一致。

**构建输出必须绑定到文件（OHOS worker 现象）**

本包首次提交前运行时发现：`conan create` 的 `build()` 中直接 `self.run("make ...")`，
在 W3 本地 CI（`ci/conan/build_and_test.sh`，其输出经 `tee` 走管道）下，
第一条 `clang -c ... wiseconfig.c` 会以非 0 码退出且**不产生任何诊断**，
而同一目录手工执行同一命令则正常。根因是 OHOS worker 上编译器/链接器输出
走管道时会被静默丢弃并把命令判为失败。配方因此改为 `_run_logged()`：
每个构建/测试步骤在命令内部 `> <log> 2>&1` 绑定日志文件，失败时再把日志末尾
回显到 conan 输出。改后 W3 全程通过（L0 pass / L1 pass / L5 pass，
test_package 7 组断言全绿）。

**配方要点**

- `package_type = "application"`（R38），产物为上游 `make bin` 清单的 11 个程序：
  `genewise`、`genewisedb`、`estwise`、`estwisedb`、`dnal`、`psw`、`pswdb`、`dba`、
  `promoterwise`、`scanwise`、`scanwise_server`；软件级 `commands.json` 已按 R38 提供。
- 构建固定 `-j1`（R9）；编译器与 CFLAGS 全部由配方计算后经 make 命令行传入（R33）。
- 其他必需 flags：`-fcommon`（2007 年代码依赖 tentative definition 合并，clang 15 默认
  `-fno-common` 会报 multiple definition）、`-Wno-error=int-conversion`（上游
  `void*`→`char` 赋值，与 Debian wise 2.4.1-25 起的处理一致）。
- 运行期数据（`BLOSUM62.bla`、`codon.table`、`human.gf`、`gene.stat` 等 29 个文件）安装到
  `share/wise/wisecfg`，并由 `package_info()` 的 `runenv_info` 导出 `WISECONFIGDIR`；
  `resdirs = ["share"]`。非 Conan 场景需手动 `export WISECONFIGDIR=<prefix>/share/wise/wisecfg`。
- 依赖：glib/2.88.3.1（ohpcd 已发布，shared）；上游仅使用 glib2 仍提供的
  `g_hash_table_*` / `g_tree_*` / `g_string_chunk_*` 等接口。
- 源码：上游 EBI 站点已下线，采用 Debian 源码池镜像
  `https://deb.debian.org/debian/pool/main/w/wise/wise_2.4.1.orig.tar.gz`，
  sha256 已与 `wise_2.4.1-28.dsc` 的 `Checksums-Sha256` 交叉校验一致。

**已知限制（不影响 CI 门禁）**

1. wise2 的工具在打印版本/用法后以非 0 码退出（`genewise`/`dnal` 等为 63、`dba` 为 255、
   `promoterwise` 为 12），因此 CI 的 L2 `--version` / `--help` 冒烟探测对 11 个程序
   都不会返回 0（该层为非阻塞），`test_package` 已改为校验输出内容而非退出码。
2. `scanwise` / `scanwise_server` 为遗留网络组件，传入非法参数（如 `--version`）时上游
   缺少参数校验会异常退出；正常用法可用（实测 `scanwise_server <seq.fasta>` 正常启动并
   监听 4050 端口）。上游测试套件未覆盖这两个程序，本包与上游 `make bin` 清单保持一致保留。
3. 上游 `models/` 还会构建 `genomewise`、`sywise`、`pseudowise`，但不在上游 `make bin`
   安装清单内，本包与上游保持一致，未收录。
