# blimps 3.9 适配笔记

## 概述

BLIMPS（BLocks IMProved Searcher）是 FHCRC（Fred Hutchinson Cancer Research
Center）维护的 Blocks 蛋白质基序数据库搜索与 Block Maker 套件，官方归档发布在
NCBI：`https://ftp.ncbi.nlm.nih.gov/repository/blocks/unix/blimps/`。3.9 为该
归档中的最终版本（2006/2007 年最后一次更新，UPDATES 记录至 2007）。license 为
FHCRC non-commercial（非商业授权，tarball 根部 `LICENSE`），Debian 将其归入
non-free；本配方如实以 "FHCRC non-commercial license" 标注。

## 构建系统

- 无 configure/CMake/autoconf，只有两份 plain Makefile：
  - `blimps/Makefile.Linux`：构建 libblimps.a + 38 个可执行文件；
  - `protomat/Makefile.Linux`：9 个可执行文件（blksort/getblock/getseq/multimat/
    motifj/motomat/uextract/blosum/blastdat）。
- 上游默认 `CC=/usr/bin/gcc`（blimps）、`CC=CL=gcc`（protomat），全部在 make
  命令行覆盖，不改动 Makefile 变量。
- 上游 `make install` 仅将产物移动到源码树内 `../bin`、`../lib`，无 prefix 概念；
  `package()` 从源码树 `bin/` 收集顶层常规文件（38+9=49 个可执行）。
- 依赖闭包：仅 libc + libm。上游 `LDLIBS=-lblimps -ly -lm` 中的 `-ly`（yacc 库）
  被命令行覆盖为 `-lblimps -lm`——全树无任何 yy* 符号引用，且 OHOS 无 liby。
- 设备 make 无法创建 jobserver fifo（mkfifo 受限），必须 `make -j1`。

## 打包范围取舍

- **application**：49 个可执行文件全部打包（套件各工具协作：blocks_search→blkprob→
  blksort、motifj→motomat 等构成流水线，缺一会影响上游文档描述的用法）。
- **libblimps.a 不打包**：内部构建产物，无独立消费者（Debian 也是拆分为独立的
  libblimps-dev 包）；如后续有链接需求再评估拆分 libs/headers。
- **docs/ 数据表打包到 `share/blimps/docs/`**：工具从工作目录加载 frequency/
  scoring/codon usage 表（default.amino.frq、default.qij、arab.codon.use 等），
  属于运行必需数据。
- 所有可执行文件经 `binary-sign-tool` 自签名（OHOS 可执行要求）。

## 补丁（最小化原则，共 4 个）

命令行无法解决、必须动源码的最小集：

1. `0001-remove-stale-makedepend-block.patch`：删除 Makefile.Linux 尾部 2004 年
   makedepend 生成的依赖块（引用 `/usr/include/assert.h`、SuSE gcc 3.3 内部头等
   宿主路径）。任何非该环境构建都会在解析 target 时直接失败
   （"No rule to make target '/usr/include/assert.h'"）。删除生成物属可再生内容
   （`make depend` 可重建），语义零影响。
2. `0002-rename-legacy-getline.patch`：`util.c` 定义了一个**从未被调用**的旧式
   `getline()`（全树唯一引用点），与 OHOS musl sysroot `stdio.h` 在默认 gnu 模式
   下（无需任何特性宏）声明的 POSIX `getline` 冲突（clang 硬错误且不可用
   -Wno-error 降级；严格 ISO 模式下该声明被隐藏，实测无冲突）。重命名为
   `blimps_legacy_getline`。
3. `0003-fix-static-decl-pssm.patch`：`pssmdist.c` 的 `read_a_freq` 与 `papssm.c`
   的 `read_freq` 前向声明缺 `static`（定义处为 static），clang 15 判 error
   （"static declaration follows non-static declaration"）。声明处补 `static`。
4. `0004-rename-format-block-resize.patch`：`format_block.c` 内的 static
   `resize_block_sequences` 副本与 `include/blocks.h` 的 extern 声明冲突（正式
   定义在 `blocks.c` 且被 addseqs.o 引用，不能改为非 static）。将该文件内副本
   重命名为 `format_block_resize_sequences`（定义 + 3 处调用）。

不用补丁解决、走构建变量：

- **gets() 有界读加固（可选，非构建必需）**：OHOS musl 实际**保留可用的 `gets`
  符号**（运行时 ld-musl 导出 T 型 gets，地址独立于 fgets/getline，`llvm-nm -D
  /lib/ld-musl-aarch64.so.1` 实测）；sysroot `stdio.h` 仅按
  `#if __STDC_VERSION__ < 201112L` 门控其**声明**（C11 移除该函数），默认 gnu17
  模式下声明隐藏——不带宏编译时 `gets()` 调用点仅报
  implicit-function-declaration 告警，链接与运行均正常（设备双探针实测：nm 符号
  表 + 无宏编译运行 exit 0）。上游共 **129 处** `gets()` 调用（word-boundary
  实测全树 .c，交互式提示路径）；Debian 用 53KB 的 gets.patch/more_gets.patch
  逐点替换。本配方改用一条预处理命令行 `DEFINES/CFLAGS` 追加
  `-D'gets(s)=fgets(s,8192,stdin)'`：零源码改动覆盖全部调用面，并把无界读收敛
  为 8KB 有界读——这是**语义变更**（加固/收敛技术债，非修复必需），已在库
  README 与本节声明。
- **隐式函数声明 / int-conversion（防御性降级）**：老代码大量 K&R 风格与隐式
  声明。本工具链（clang 15.0.4 默认 gnu17）实测**仅告警非 error**（pristine
  motifj.c 去掉 -Wno-error 编译 exit=0，77 条告警 0 错误）；
  `-Wno-error=implicit-function-declaration -Wno-error=int-conversion` 为
  **防御性保留**，防上游同类 `-Werror` 开关复活。另实测上游
  `XXWARN = -Werror`（blimps/Makefile.Linux:101）为**死变量**（定义后全文件零
  引用），当前不生效。

## 实际构建命令

```bash
make -j1 -f Makefile.Linux install \
  CC=<clang> AR=<ar> RANLIB=<ranlib> \
  OPTIMIZ="-O2 -Wno-error=implicit-function-declaration -Wno-error=int-conversion" \
  DEFINES="-D'gets(s)=fgets(s,8192,stdin)'" \
  LDLIBS="-lblimps -lm"          # blimps/

make -j1 -f Makefile.Linux install \
  CC=<clang> CL=<clang> \
  CFLAGS="-O2 -D'gets(s)=fgets(s,8192,stdin)' -c"   # protomat/
```

`CC/AR/RANLIB` 从 Conan conf `tools.build:compiler_executables` 推导（同 bwa 配方）。
两处旗标均非实测必需（见上节），保留为防御性 + 加固语义。

## 测试策略

上游**没有测试套件**（NO_UPSTREAM_TESTS）：两份 Makefile 均无 test/check 目标
（仅有 install/all/lib/local/clean/tags/depend/distribution），README/UPDATES 未
描述任何测试入口；`examples/` 是 csh/perl 驱动脚本 + 样例输入，其中
`examples/blimps/distribution/example.blkprob` 等 golden 已过期（由 BLKPROB
8/22/03 生成，3.9 代码打印 12/23/06.1），不能作为全量 golden。

本配方 `test_package/test_blimps.sh` 做真实功能验证：

1. `codehop euk.blks -Carab.codon.use -O3`：全输出与上游
   `examples/codehop/distribution/euk.out` **逐行一致**（仅归一化回显的 codon
   表路径字符串）；codehop 需要工作目录有 default.amino.frq + identity.frq +
   codon 表，否则结果不同（已实测验证该依赖）。
2. `blimps`（.cs 搜索参数文件：example.pro vs sample.blocks）：全输出与上游
   `examples/blimps/distribution/example.bli` **逐行一致**（仅归一化 Probe File
   路径回显行），并断言 `Records Searched: 9`。
3. `blkprob`：对同一搜索做结果分析，断言输出含 Database/Query 信息（其专属
   golden 已过期，不做全量比对）。
4. `motifj 4 -lipo.pros`：Block Maker 在 PROSITE 脂蛋白样例上构造 blocks，
   断言 lipo.mot / lipo.motifj.pros 非空。

以上均在移植前于设备上用本配方构建产物实测通过（codehop/blimps 与 golden
逐字节一致）。

## 已知限制与风险

- **固定长度路径缓冲区**：.cs 等配置文件的路径字段被 strcpy 进小缓冲区（实测
  约 32 字节量级），长绝对路径会截断/损坏。工具应在工作目录内用短文件名运行；
  这是上游设计限制，非 OHOS 回归，已在库 README 中提示。
- `--version`/`--help` 非上游约定，CI L2 冒烟可能给出非阻塞 warning；功能测试
  已覆盖真实命令链。
- tarball 内带有预编译的 bin/OSX、bin/Linux 等历史二进制，本配方仅打包源码树
  顶层新构建产物，不触碰预编译目录。
- FHCRC non-commercial license 限制商用分发，使用方需自行确认授权范围。
