# minigraph 0.21 — HarmonyOS PC 适配笔记

## 软件概述
minigraph（作者 Heng Li，lh3）是序列-图比对工具：以第一个输入为参考（FASTA 或
已有 GFA 图），把后续输入的组装序列（FASTA）比对到参考上，将 >= 阈值的结构变异
插入图中，输出增广后的 GFA 变异图（`-cxggs` 建图预设）；也可把长读/序列比对到
已有图上输出 PAF（默认）或 GAF（图坐标，`-x` lr/asm 预设）。核心为纯 C99 实现
（内嵌 klib 头文件），zlib 支持压缩输入，pthread 多线程。

## 源码来源
- 上游仓库：https://github.com/lh3/minigraph （官方唯一仓库，作者 lh3）
- 上游主页：https://lh3.github.io/minigraph/
- 0.21 版本：tag `v0.21`，发布于 2024-07-13，版本串 `0.21-r606`
  （见 minigraph.h MG_VERSION）
- 官方源码 tarball：`https://github.com/lh3/minigraph/archive/refs/tags/v0.21.tar.gz`
  （上游无 GitHub Release asset，tag 归档即官方源码包；不使用任何第三方 fork）
- SHA256：`4272447393f0ae1e656376abe144de96cbafc777414d4c496f735dd4a6d3c06a`
  （codeload.github.com 与 gh-proxy 镜像两个独立源下载比对，逐字节一致）
- License：MIT（LICENSE.txt，Copyright (c) 2016-2019 Broad Institute）
- 解压后顶层目录：`minigraph-0.21/`

## 上游测试核查（结论：无正式测试）
逐项核查过 v0.21 tarball 与上游仓库：
1. **Makefile**：仅 all/clean/depend 目标，**无 test/check 目标**。实际执行
   `make test` 报 `make: Nothing to be done for 'test'.`（rc=0——make 把已存在
   的 `test/` 目录当作无规则但已是最新 的目标，并非真有测试目标）；
   `make check` 报 `make: *** No rule to make target 'check'.  Stop.`（rc=2）。
   两者均无任何测试被执行。
2. **test/ 目录**：只包含 4 个 README quick-start 示例数据文件
   （`MT-human.fa`、`MT-chimp.fa`、`MT-orangA.fa` 三个线粒体 FASTA +
   `MT.gfa` 预建图），无任何脚本、无期望输出文件。
3. **tests/ 目录**：不存在。
4. **shell/python 测试脚本**：仓库无 .sh/.py 测试脚本。
5. **CI workflow**（.github/workflows/）：仓库无任何 workflow 文件
   （GitHub Actions 目录不存在），无 CI 测试。
6. **Release tarball 测试内容**：与 repo 一致，无额外测试。

README 的 quick-start（`./minigraph -cxggs test/MT.gfa test/MT-chimp.fa` 两步
建图 + 比对示例）是唯一官方演示用法，本适配将其作为上游示例功能验证执行，不计
入正式测试数量。

### 上游示例功能验证（OHOS AArch64 工具链真实运行）
- 构建：`make CC=clang LIBS="-L<zlib> -lz -lpthread -lm"` → 成功，零 patch，
  仅 -msse4 在 AArch64 上的 unused-command-line-argument 无害警告。
- README quick-start：从 MT.gfa 增广 chimp → S=8 L=11 结构保持；比对
  orangA 输出含 `>MTh` 路径命中的 PAF 行，功能正常。
- 确定性：同输入重复运行输出逐字节一致。
- **上游正式测试：Total 0 / Pass 0 / Fail 0 / Skip 0**。
- 负向行为：`minigraph nosuch.fa` → rc=1 + `ERROR: failed to open nosuch.fa`。

## 编译环境
- 构建系统：makefile（plain make，无 configure、无 install 规则）
- 编译日期：2026-09-11
- 编译器：clang（通过 Conan conf `tools.build:compiler_executables:c` 获取，R33；
  本机为 /storage/Users/currentUser/usr/local/bin/clang，aarch64-unknown-linux-ohos）
- 状态：built

## 编译步骤
1. `source()` 下载并解压官方 tag tarball（strip_root=True）
2. `build()`：`make -C <src> CC=<conan conf 获取的 clang> CFLAGS="<上游原样 +
   -msse4 过滤 + 三重 -ffile-prefix-map>" LIBS="-L<zlib libdir> -lz -lpthread
   -lm" -j1`
   - 上游 CFLAGS（-g -Wall -Wc++-compat -std=c99 -msse4 -O3）逐字保留，仅在
     AArch64 目标上滤除 x86 专属 -msse4（见下文"### 3"），其余零 patch
   - -ffile-prefix-map×3：source_folder + build_folder（make -C 下编译器 cwd
     是 source_folder，DWARF comp_dir 记录的是它）+ 工具链根目录（sysroot
     头文件路径）；映射后二进制 strings 扫描零宿主路径（R 可复现交付）
     （详见 knowledge/drafts/DRAFT-E579-minigraph-dwarf-compdir-host-path-leak.kv）
   - LIBS 覆盖原因：Makefile 默认 `-lz -lpthread -lm`，`-lz` 若不指定路径会解析到
     sysroot/系统的 zlib；改为指向 Conan zlib 包的 libdir（R26 系统名库走 Conan）
   - -j1：环境 jobserver mkfifo 受限（Operation not permitted），并发 make 报错
3. `package()`：copy `minigraph` 可执行文件 → bin/（上游无 install 规则）

## 关键适配点

### 1. zlib 依赖（唯一外部依赖）
bseq.c / gfa.c 内嵌的 kseq.h 使用 `<zlib.h>` 读写 .fa/.fa.gz/.gfa/.gfa.gz 输入。
zlib 经 `self.requires("zlib/1.3.1")` 引入（制品仓已发布 zlib/1.3.1，无传递
冲突）。构建期库搜索路径由 Conan zlib 包提供（`-L<zlib cpp_info.libdirs[0]>`）；
最终二进制 NEEDED = libz.so + libc.so + libpthread 不出现（musl 内置）。

### 2. 编译器覆盖（R33）
Makefile 默认 `CC=gcc` 且 Makefile 内 `CC=` 赋值优先于环境变量，必须用 make
命令行参数覆盖为 Conan conf 获取的 clang；recipe 无任何硬编码路径（无
/storage、无 /data/service/hnp、无用户名）。

### 3. -msse4 的 AArch64 处理
Makefile CFLAGS 含 x86 专属 `-msse4`，grep 证实源码无任何 SSE intrinsic
（minigraph 的 SIMD 路径在 sketch/simd 之外无 ksw_sse 之类调用）。该 flag 是
x86 ISA 选择器，在 AArch64 上不启用任何代码路径，但 clang 每个文件都会警告
unused command line argument（30 个 .c × 每文件一条）。处理：目标 arch 为
AArch64/armv8 时 recipe 从 CFLAGS 中精确滤除 `-msse4`（其余上游 flag 逐字
保留），其他目标（x86 等）不动。这保持构建无警告且不改变代码生成，仍是零
patch（只经 make 命令行传 CFLAGS，不改上游文件）。

另：OHOS clang wrapper（/usr/local/bin/clang）自身向每次调用（含 -c 编译）
注入 `-fuse-ld=lld -Wl,--code-sign -L<sysroot>` 等链接 flag，也会触发同类
警告。跟随仓库惯例（binutils、gdal 配方同例），OHOS 上追加
`-Wno-unused-command-line-argument` 抑制。

### 4. 无 install 规则
上游 `make install` 不存在，package() 手工 copy 唯一用户产物 `minigraph` 到
bin/。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-lz` 链到 sysroot zlib | Makefile 默认 LIBS 无库路径 | LIBS 传 `-L<zlib libdir> -lz`（R26） |
| 2 | 上游无 make install | 上游只提供构建目标 | package() 手工 copy minigraph → bin/ |
| 3 | `--help`/无参 rc=1 可能影响 L2 | 上游 Usage 打到 stderr 且 rc=1 | L2 用 `--version`（rc=0） |
| 4 | 建图输出无气泡（S=1 L=0） | ggs 预设 min_map_len 默认 100000、min_depth_len 默认 20000，小输入全部被过滤 | 建图命令显式加 `-l/-d` 降阈值（合成 fixture 用 -l1k -d1k；MT 用 -l10k -d10k） |
| 5 | make -j2+ 报 jobserver mkfifo Operation not permitted | 环境限制 | build() 固定 -j1 |

## 依赖
- zlib/1.3.1（Conan 包，kseq 读 gzip 输入）
- 其余：libc + libm + libpthread（OHOS musl 自带）

## test_package 设计
fixture 为程序化生成的确定性文本 FASTA（无二进制、无来源不明数据）：
- `testdata/ref.fa`：ref1 = 16000bp 固定种子 LCG 随机序列（建图参考）
- `testdata/sample.fa`：sam1 = 15000bp = ref[:4000] + ref[5000:]
  （相对参考在 4000 处缺失 1000bp，单一明确的结构变异注入）
- 比对测试：图（GFA）与线性参考（FASTA）双模式

断言（test_minigraph.sh，18 条：功能 1-14 + 鸿蒙特有 15-18）：
1. `--version` 输出 `0.21-r606`（rc=0）
2. 建图（-cxggs -c -l1k -d1k ref.fa sample.fa）：输出 S 行 >= 2 且 L 行 >= 1
   （结构变异被插入图成气泡，非单段直链）
3. 建图段序列只含 ACGT（结构化输出合法性）
4. 建图确定性：同输入两次运行输出逐字节一致（cmp）
5. GFA L 行 CIGAR 合法（^[0-9]+M$ 或 *）
6. 线性映射（minigraph ref.fa sample.fa）：PAF 恰好 1 行命中 sam1→ref1
7. PAF 字段：strand=+、目标长度 16000、query/target block 与区间自洽
8. 图映射（-cxlr graph.gfa sample.fa）：GAF 输出 >= 1 行且含 ds:Z 图坐标
   标签（GAF 特有、PAF 不出现的图路径标签）
9. 手写 GFA 输入（H 行 + 单 S 行带 SN:Z/SO tags，非 minigraph 自产）：被
   接受为映射目标，单行 GAF 报告 NM:i:1000 精确等于注入的 1000bp 缺失
10. `--call` 变异检测（-xasm -l1k -d1k --call graph.gfa sample.fa）：BED
   首行 ref1:4000-5000 与注入位置精确一致
11. gz 输入：gzip 压缩的参考输入正常比对（zlib 链路验证）
12. 负向：缺失图输入（第一参数）→ rc=1 且 stderr 含 `failed to load the graph`
13. 负向：缺失样本输入（第二参数）→ rc=1 且 stderr 含 `failed to open`
    （与 12 是不同错误代码路径，各占一条断言）
14. 负向：空参数 → rc=1 且 stderr 非空（Usage）
15. 鸿蒙：纯 Python 解析 ELF — ELF64 小端 + AArch64(e_machine=0xB7) +
    PIE(ET_DYN) + musl PT_INTERP(/lib/ld-musl-aarch64.so.1) + .codesign 段
16. 鸿蒙：动态段无 DT_RPATH/DT_RUNPATH；DT_NEEDED 仅 libz/libc/libm/libpthread
17. 鸿蒙：二进制字节级扫描无 /storage/、/home/、/Users/、/data/service
    （-ffile-prefix-map 效果验证）
18. 鸿蒙：部署模式真实运行建图，产出气泡结构（S>=2/L>=1）
（非 OHOS aarch64 宿主上 15-18 自动 SKIP 并明示）

### 验证记录（本地构建）
- `file`：ELF 64-bit LSB arm64, dynamically linked, interpreter
  /lib/ld-musl-aarch64.so.1, PIE（Type DYN）
- readelf：Class ELF64 / Machine AArch64 / INTERP /lib/ld-musl-aarch64.so.1 /
  .codesign 段存在 / 无 RPATH、无 RUNPATH
- NEEDED：libz.so, libc.so
- L4 静态安全：GNU_STACK RW（NX 启用，无 E）、ET_DYN PIE、GNU_RELRO +
  BIND_NOW（Full RELRO）
- strings 宿主路径扫描：零命中（/storage、/home、/Users、/data/service 均无）
- L1e 破坏性反向验证：移走包内 bin/ 后 conan test 失败（rc=1），恢复后
  17/17 通过 — 测试真实依赖被测包产物（R34）
- 本机即 HarmonyOS PC（aarch64-ohos），构建产物直接真实运行通过
