# wise 2.4.1 测试报告（HarmonyOS PC aarch64）

> **项目**: wise（EBI Wise2 / Dynamite）2.4.1
> **测试日期**: 2026-09-23
> **测试环境**: HarmonyOS / OpenHarmony PC aarch64（`aarch64-linux-ohos`），clang 15.0.4，musl sysroot
> **测试类型**: 官方测试套件（上游 `src/test/short.test`）+ 鸿蒙特有测试（test_package 7 个完整端到端消费者用例）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试用例总数 | 12 | 100% |
| 通过 (PASS) | 12 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 新增（鸿蒙特有）测试 | 7 个完整端到端消费者用例（含 40+ 条断言） | 100% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。11 个命令行程序在 HarmonyOS PC aarch64 下全部可构建、可运行；
上游 12 个集成用例全部通过，比对结果与上游参考输出逐字节一致。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 | 状态 |
|----------|----------|----------|------|
| AArch64 `char` 无符号导致 `EOF` 判定失效 | 全部序列读取路径（长度 +1、坐标偏移、部分段错误） | 🔴 | 已修复（`-fsigned-char`） |
| `glib-config`（glib 1.2 时代工具）缺失 | 全部 9 个 makefile 的编译/链接 | 🟡 | 已修复（补丁 0001） |
| HMMer2 局部 `getline()` 与 POSIX 冲突 | HMMer2 库（`sqio.c`） | 🟡 | 已修复（补丁 0003） |
| `isnumber()` 为 BSD 专有接口 | genewise/estwise/genewisedb/estwisedb | 🟡 | 已修复（补丁 0004） |
| `csh` 依赖 | `make bin` 目标 | 🟢 | 已修复（补丁 0002） |
| L2 冒烟 `--version` 非 0 退出 | CI 非阻塞告警 | 🟢 | 上游既有行为，非阻塞 |

### 2.3 可用功能清单

```
✅ genewise          蛋白 × 基因组 基因结构预测（核心工具）
✅ genewisedb        genewise 的序列库搜索模式
✅ estwise           蛋白 × EST/cDNA 比对
✅ estwisedb         estwise 的序列库搜索模式
✅ dnal              DNA × DNA 局部比对
✅ psw               蛋白 × 蛋白 Smith-Waterman 比对
✅ pswdb             蛋白库 Smith-Waterman 搜索
✅ dba               database alignment
✅ promoterwise      启动子区比对
✅ scanwise          scanwise 客户端
✅ scanwise_server   scanwise 服务端（实测可启动并监听 4050 端口）
```

### 2.4 已知限制

1. 工具在打印版本/用法后以非 0 码退出（`genewise`/`dnal`/`estwise`/`estwisedb`/
   `genewisedb`/`psw` 为 63，`dba` 为 255，`promoterwise` 为 12，
   `pswdb` 为 1）——上游既有行为，`test_package` 因此只校验输出内容，不校验退出码。
2. `scanwise` / `scanwise_server` 为遗留网络组件，对非法参数缺少校验
   （`scanwise_server --version` 会把 `--version` 当文件名）。上游测试套件未覆盖
   这两个程序；本包与上游 `make bin` 清单保持一致。
3. 上游 `models/` 还会构建 `genomewise`、`sywise`、`pseudowise`，不在上游
   `make bin` 安装清单内，本包未收录。

---

## 三、测试详情

### 3.1 通过的测试（层 1：上游官方测试套件）

执行方式（`conanfile.py` 的 `build()` 内，`conan create` 时自动执行）：

```bash
cd <source_folder>/src/test
perl testman.pl -cf ../wisecfg < short.test > upstream-test.log 2>&1
# 判定：grep -q 'Tests passed' upstream-test.log && test ! -s test.results
```

| 测试项 | 功能 | 结果 |
|--------|------|------|
| promoterwise | promoterwise 标准测试（human vs mouse 启动子区） | ✅ PASS |
| basic-cdna | estwise 蛋白 vs cDNA，全输出选项 | ✅ PASS |
| basic-genomic | genewise 蛋白 vs 基因组，全输出选项 | ✅ PASS |
| hmm-binary-cdna | estwise 以二进制 HMM 为 query | ✅ PASS |
| hmm-wrong-dna | genewise HMM vs 无匹配 DNA | ✅ PASS |
| hmm-wrong-dna-est | estwise HMM vs 无匹配 DNA | ✅ PASS |
| hmm-ascii-genomic | genewise 以 ASCII HMM 为 query | ✅ PASS |
| genewise-db | genewisedb HMM vs DNA 库 | ✅ PASS |
| genewise-db-lite | genewisedb GWLITE 算法 | ✅ PASS |
| estwise-db | estwisedb HMM vs DNA 库 | ✅ PASS |
| pswdb | pswdb 蛋白库 Smith-Waterman 搜索 | ✅ PASS |
| genewisedb-pfam-mode | genewisedb Pfam 搜索模式 | ✅ PASS |

### 3.2 通过的测试（层 2：鸿蒙特有测试 = test_package 完整端到端消费者用例）

`test_package/test.sh` 在 `conanrun` 运行环境内执行。每个用例都是一条完整的
端到端消费者流程：**消费者构造输入 → 真实执行包内安装的程序 → 程序读取包导出的
`WISECONFIGDIR` 运行期数据 → 产出真实比对结果 → 校验结果内容**，
任一环节失败即该用例 FAIL，最终以「通过用例数 / 用例总数」为结果（实测 7/7）。

| 用例 | 端到端流程 | 结果 |
|------|-----------|------|
| HC-1 | 消费链路入口：11 个程序经 PATH 可定位；包导出的 `WISECONFIGDIR` 含 BLOSUM62.bla / codon.table / gene.stat / human.gf 且可读；11 个程序 `-version` 均真实执行并报告 `wise2-4-1` | ✅ PASS |
| HC-2 | genewise 蛋白 × 基因组 DNA 比对：query/target 名、`Comp Matrix: BLOSUM62.bla`、`Codon Table: codon.table`、`Gene Parameter file: gene.stat` 均加载成功，含 rrm 保守肽段 `DYDPVDKVVLQKQHQLNGK`，含结束标记 `//` | ✅ PASS |
| HC-3 | estwise 蛋白 × cDNA 比对：含保守肽段与结束标记 `//` | ✅ PASS |
| HC-4 | dnal DNA × DNA 局部自比对：得分 `Score 2065`（确定性，与上游 `test/basic_cdna` 基线一致），含序列名 HSHNCPA1 | ✅ PASS |
| HC-5 | psw 蛋白 × 蛋白 Smith-Waterman：含 rrm 保守肽段与结束标记 `//` | ✅ PASS |
| HC-6 | dba DNA × DNA DBA 块自比对：`score = 695.64`，100% 覆盖、判定 `MATCH_D` | ✅ PASS |
| HC-7 | promoterwise 双 DNA 启动子预测：走完 `Search....done` 搜索阶段，产出 BLAST 格式报告，命中 HSHNCPA1、`Length = 415`（415 为 short.dna 真实长度）、含 `Sbjct:` 比对区段 | ✅ PASS |

```
================ 用例汇总 ================
通过: 7 / 7
✅✅ wise 2.4.1 鸿蒙特有测试全部通过（7 个完整端到端消费者用例）
```

### 3.3 失败的测试

无。

### 3.4 跳过的测试

无。上游 `src/test/short.test` 用例为端到端集成测试（真实执行交叉编译产出的
aarch64 二进制并 diff 参考输出），在 OHOS aarch64 worker 上可直接执行，无需跳过。

---

## 四、关键问题分析

### 问题1: 上游测试仅 4/12 通过 —— AArch64 `char` 默认无符号导致 `EOF` 判定失效

**现象**（未加 `-fsigned-char` 时）：

```
Error in promoterwise: <  Length = 798 Reversed 1
Error in promoterwise: >  Length = 797 Reversed 1     # 参考（pw.mouse 真实长度 797）
Error in basic-cdna:   < 3.75 [31:32 "MATCH_STATE" 1301],[98:101 "CODON" 1301]
Error in basic-cdna:   > 3.75 [31:32 "MATCH_STATE" 1301],[97:100 "CODON" 1301]
Signal 11 (core dumped)      # estwise / estwisedb / basic-cdna
```

**根因分析**：

`dynlibsrc/sequence.dy`/`.c` 的 FASTA 读取器使用 `char` 变量接收 `fgetc()`：

```c
char c;                        /* ← AArch64 上 char 默认无符号 */
...
c = fgetc(ifp);
if( c == EOF || c == '>' || c == '/' ) break;   /* ← 无符号 char 下 EOF(-1) 永不相等 */
```

在 AArch64（AAPCS64）上 `char` 默认为 **unsigned char**，`c == EOF` 中 `c` 提升为
255 而 `EOF` 为 -1，比较恒假：文件结束时读到的 `EOF` 不被识别为结束，
`seqbuffer[i++] = c` 把 `0xFF` 当作一个碱基写入序列。后果：

- 序列长度比真实值多 1（`798` vs `797`）；
- 下游所有 DNA/CODON 坐标整体偏移（`[98:101]` vs `[97:100]`）；
- 部分组合下位点在后续解析中越界，进程 SIGSEGV。

x86_64 上 `char` 默认为有符号，因此上游与该代码的原作者都观察不到此问题。

**解决方案**：

配方编译标志加入 `-fsigned-char`，使 `char` 恢复该代码在 x86 上的原始语义。
不采用逐处修改 `char c;` → `int c;` 的方式，是因为该模式散布在
`dynlibsrc/sequence.c` 等多处（本仓统计 11 处 `char`/`EOF` 比较），
全局标志可一次性覆盖全部路径（含上游测试未覆盖的代码），且不产生
`.c` 与 `.dy` 预生成文件的额外分叉。

验证：加入该标志后上游测试 **4/12 → 12/12**，唯一变量即为该标志。

### 问题2: `glib-config` 缺失导致配置阶段即失败

**现象**：`sh: glib-config: not found`；链接期 `undefined reference to g_hash_table_*` 等。

**根因**：上游 makefile 使用 glib 1.2 时代的 `glib-config --cflags/--libs`，
现代系统只提供 `pkg-config`，且 glib2 的 `.pc` 依赖 `proxy-libintl` 等虚拟包。

**解决方案**：补丁 0001 将 9 个 makefile 中的反引号调用替换为 make 变量
`$(GLIB_CFLAGS)` / `$(GLIB_LIBS)`，由配方从 `self.dependencies["glib"].package_folder`
计算后经 make 命令行传入（make 命令行变量会自动传递给递归子 make）。

---

## 五、测试环境

```
目标平台 : aarch64-linux-ohos（OpenHarmony / HarmonyOS PC）
编译器   : clang 15.0.4 (/data/service/hnp/bin/clang)
C 库     : musl（OHOS sysroot 26.0.0.18）
构建工具 : conan 2.29.1（OHOS 适配版）/ GNU Make 4.4.1 / perl 5.42.0
Profile  : ci/conan/profiles/ohos-aarch64（host = build = ohos-aarch64）
依赖     : glib/2.88.3.1（ohpcd，shared）
编译标志 : -c -O2 -DUNIX -pthread -fcommon -fsigned-char -Wno-error=int-conversion
           $(pkg-config 等价的 glib include 路径)
产物     : bin/ 下 11 个可执行程序 + share/wise/wisecfg/ 下 29 个运行期数据文件
```

---

*报告生成时间: 2026-09-23（2026-09-24 按评审意见补充 HC-6/HC-7 两个端到端消费者用例）*
