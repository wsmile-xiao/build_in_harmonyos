# miniprot 0.18 — HarmonyOS PC 适配笔记

## 软件概述
miniprot（作者 Heng Li，lh3）是将蛋白质序列比对到基因组上的工具，建模了剪接
（内含子，GT..AG 等剪接位点）与移码，输出 PAF（默认）或 GFF3（--gff）格式的
比对结果，常用于基因注释、同源基因查找。核心为纯 C99 实现（内嵌 klib 头文件），
SSE 加速的氨基酸比对动态规划（nasw-sse.c）。

## 源码来源
- 上游仓库：https://github.com/lh3/miniprot （官方唯一仓库，作者 lh3）
- 上游主页：https://lh3.github.io/miniprot/
- 0.18 版本：tag `v0.18`，commit 671db243f964a68bd724af11cd9964d840f29c43，
  发布于 2025-07-11，版本串 `0.18-r281`（见 NEWS.md 与 miniprot.h MP_VERSION）
- 官方源码 tarball：`https://github.com/lh3/miniprot/archive/refs/tags/v0.18.tar.gz`
  （上游无 GitHub Release asset，tag 归档即官方源码包；不使用任何第三方 fork）
- SHA256：`e1b5c08571fa3a4aa225da8ec9c6e744cd116b4dc50d9e187114cffe336921ee`
  （gh-proxy 与 codeload.github.com 两个独立源下载比对，逐字节一致）
- License：MIT（LICENSE.txt，Copyright (c) 2022- Dana-Farber Cancer Institute）
- 解压后顶层目录：`miniprot-0.18/`

## 上游测试核查（结论：无正式测试）
逐项核查过 v0.18 tarball 与上游仓库：
1. **Makefile**：仅 all/clean/depend/libminiprot.a/miniprot/miniprot-lite 目标，
   **无 test/check 目标**。实际执行 `make test`、`make check` 均报
   `make: *** No rule to make target 'test'/'check'.  Stop.`
2. **test/ 目录**：只包含两个 fixture 文件（`DPP3-hs.gen.fa.gz` 人类 DPP3 基因组
   区段、`DPP3-mm.pep.fa.gz` 小鼠 DPP3 蛋白），无任何脚本、无期望输出文件。
3. **tests/ 目录**：不存在。
4. **shell/python 测试脚本**：仓库无 .sh/.py 测试脚本（tex/ 是文档源码）。
5. **examples**：example.c 是 miniprot-lite 库用法示例（仅编译目标，不在测试中）。
6. **CI workflow**（.github/workflows/ci.yaml）：两个 job（build / build-aarch64）
   都只跑 `make CC=gcc|clang`，**编译后不运行任何测试**。
7. **Release tarball 测试内容**：与 repo 一致，无额外测试。

README 第 10-12 行的 quick-start（`./miniprot test/DPP3-hs.gen.fa.gz
test/DPP3-mm.pep.fa.gz`）是唯一官方演示用法，本适配将其作为上游示例功能验证执行，不计入正式测试数量。

### 上游示例功能验证（OHOS AArch64 工具链真实运行）
- 构建：`make CC=clang`（即上游 CI 的编译矩阵）→ 成功，零 patch，仅 clang 15 对
  sysroot `-L` 参数的无害 warning（编译阶段 unused，链接阶段正常生效）。
- README quick-start：PAF 输出 1 行命中（ENSMUSP00000025851.4 → chr11 区段，
  AS:i:3031，cg 含 N(内含子)/U(移码码标)；--gff 输出 21 行（1 mRNA + 18 CDS +
  1 stop_codon + 头部）。
- 确定性：同输入重复运行输出 md5 一致。
- **上游正式测试：Total 0 / Pass 0 / Fail 0 / Skip 0**。README quick-start 的 PAF/GFF 两个功能场景均验证通过，但仅作为上游示例功能验证，不计入正式测试数量。
- 负向行为：`miniprot nonexistent.fa test/DPP3-mm.pep.fa.gz` →
  rc=1 + `[ERROR] failed to open/build the index`。

## 编译环境
- 构建系统：makefile（plain make，无 configure、无 install 规则）
- 编译日期：2026-09-01
- 编译器：clang（通过 Conan conf `tools.build:compiler_executables:c` 获取，R33；
  本机为 /storage/Users/currentUser/usr/local/bin/clang，aarch64-unknown-linux-ohos）
- 状态：built

## 编译步骤
1. `source()` 下载并解压官方 tag tarball（strip_root=True）
2. `build()`：`make CC=<conan conf 获取的 clang> LIBS="-lpthread -L<zlib libdir>
   -lz -lm" -j1`
   - 上游 CFLAGS（-std=c99 -g -Wall -O3）原样保留，零 patch
   - LIBS 覆盖原因：Makefile 默认 `-lpthread -lz -lm`，`-lz` 若不指定路径会解析到
     sysroot/系统的 zlib；改为指向 Conan zlib 包的 libdir（R26 系统名库走 Conan）
3. `package()`：copy `miniprot` 可执行文件 → bin/（上游无 install 规则；
   libminiprot.a 是内部构建产物，上游也不安装，不打包）

## 关键适配点

### 1. zlib 依赖（唯一外部依赖）
bseq.c / index.c / ntseq.c / example.c 内嵌的 kseq.h 使用 `<zlib.h>` 读写
.fa/.fa.gz 输入。zlib 经 `self.requires("zlib/1.3.1")` 引入（制品仓已发布
zlib/1.3.1，无传递冲突）。构建期头文件与库搜索路径由 Conan zlib 包提供
（`-L<zlib cpp_info.libdirs[0]>`）；最终二进制 NEEDED = libz.so + libc.so，
zlib 以动态方式由 OHOS 运行时/sysroot 提供（详见验证记录）。

### 2. 编译器覆盖（R33）
Makefile 默认 `CC=gcc`，通过命令行 `CC=` 覆盖为 Conan conf 获取的 clang；
recipe 无任何硬编码路径（无 /storage、无 /data/service/hnp、无用户名）。

### 3. 无 install 规则
上游 `make install` 不存在，package() 手工 copy 唯一用户产物 `miniprot` 到 bin/。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-lz` 链到 sysroot zlib | Makefile 默认 LIBS 无库路径 | LIBS 传 `-L<zlib libdir> -lz`（R26） |
| 2 | 上游无 make install | 上游只提供构建目标 | package() 手工 copy miniprot → bin/ |
| 3 | `--help` rc=1 可能影响 L2 | 上游 Usage 打到 stderr 且 rc=1 | L2 用 `--version`（rc=0） |

## 依赖
- zlib/1.3.1（Conan 包，kseq 读 gzip 输入）
- 其余：libc + libm + libpthread（OHOS musl 自带）

## test_package 设计
fixture 为程序化生成的确定性文本 FASTA（无二进制、无来源不明数据）：
- `genome.fa`：ctg1 = 正链两外显子合成基因（编码 avGFP 239aa，中间 150bp 内含子
  GT..AG，两侧随机侧翼，seed 固定）；ctg2 = 同 CDS 的反链无内含子拷贝
- `protein.fa`：avGFP 239aa 查询序列
- `random_neg.fa`：与基因组无关的随机 80aa 蛋白（负向输入，期望零命中）

断言（test_miniprot.sh，12 条）：
1. `--version` 输出 `0.18-r281`（rc=0）
2. PAF 比对输出恰好 2 行命中（ctg1 正链 + ctg2 反链）
3. ctg1 命中：qstart=0/qend=239（蛋白全覆盖）、strand=+、coverage 列=717/717、
   AS 分数存在且 >0、cg 含 N（内含子建模）
4. ctg2 命中：strand=-、coverage=717/717
5. GFF 模式：`##gff-version 3` 头、mRNA 行 2 条、CDS 行数 ≥3（ctg1 两条外显子 +
   ctg2 一条）、ctg1 的两条 CDS 位于 mRNA 范围内且呈二段式结构
6. cs:Z 标签存在（比对一致性序列）
7. 负向：随机蛋白 → 输出 0 行（rc=0，显式断言无命中）
8. 文件不存在输入：rc=1 且 stderr 含 `failed to open`（真实错误行为，无 || true）

## 验证记录（本地构建）
- `file`：ELF 64-bit LSB arm64, dynamically linked, interpreter
  /lib/ld-musl-aarch64.so.1, PIE（Type DYN）
- readelf：Class ELF64 / Machine AArch64 / INTERP /lib/ld-musl-aarch64.so.1
- NEEDED：libz.so, libc.so
- 本机即 HarmonyOS PC（aarch64-ohos），构建产物直接真实运行通过
