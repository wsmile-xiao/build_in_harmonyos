# minibwa 0.7 适配笔记

## 编译环境
- 构建系统: makefile (raw Makefile, 无 configure)
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (OHOS SDK, 本机 usr/local/bin)
- 状态: built

## 编译步骤

```bash
# 源码: GitHub lh3/minibwa v0.7 (r421), MIT 许可
# 上游是 raw Makefile 项目: 产物 = minibwa 二进制 + libminibwa.a
make -j1 CC=clang AR=llvm-ar ARCH=aarch64 \
     INCLUDES="-I<zlib-pkg>/include" \
     LDFLAGS="-L<zlib-pkg>/lib" \
     gpl=1 mimalloc=0
```

关键点:
1. **ARCH 显式传递**: Makefile 用 `ARCH=$(shell uname -m)` 探测架构,
   本机即 aarch64 所以探测值恰好正确,但容器/交叉场景下必须显式传
   `ARCH=aarch64`。x86_64 才会追加 `-msse4.2 -mpopcnt`;aarch64 SIMD
   走 ksw2 内置的 s2n-lite.h NEON 翻译层,无需额外 flag。
2. **串行 make**: `-j1` —— HMDFS 工作区无法承载 GNU make jobserver
   FIFO(E074),且构建体量小,串行足够。
3. **zlib 注入**: 唯一引用点是 bseq.c:8 `KSEQ_INIT2(, gzFile, gzread)`;
   上游 `LIBS=-lpthread -lz -lm` 是裸 `-lz`,通过 Makefile 的
   `INCLUDES`/`LDFLAGS` 变量注入 Conan zlib 包路径。
4. **OMP 探测**: Makefile 自动探测 OpenMP 可用性(omp=1 → -fopenmp +
   LIBSAIS_OPENMP),OHOS clang15 + libomp 可用,保持默认。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./minibwa version` 等**所有子命令** SIGSEGV(core dumped),但无参数时 usage 正常 | mimalloc 的 malloc override(`MI_MALLOC_OVERRIDE`)在 OHOS 上与 emulated TLS 冲突:第一次 malloc 发生在 emutls bootstrap 内部,`__emutls_get_address` 尚未就绪即递归进入 allocator,无限递归 → 栈溢出。ASan 定位:`stack-overflow ... in __emutls_get_address` | 上游官方开关 `mimalloc=0`(清空 MALLOC_O + `-DHAVE_KALLOC`,kalloc.o 本就在 LOBJS)——recipe 默认 `with_mimalloc=False`,OHOS 上显式禁用并 validate 拒绝(知识 E210 覆盖此模式) |
| 2 | GitHub 直连 443 超时(curl exit 28) | 网络环境限制 | conandata.yml 用 gh-proxy 镜像列表(同 aaphoto 0.45 先例) |

诊断过程(问题 1,本机真实执行,ASan 复现日志见下):
- 现象:所有写索引/读数据的子命令(index/map/fa2bit/genraw)崩溃,
  无参数 usage、`--help` 正常——崩溃点在第一个大块内存分配。
- ASan 重建(`make asan=1`,即 mimalloc=1 + -fsanitize=address):
  ```
  ERROR: AddressSanitizer: stack-overflow on address ... T0
      #0 ... in __emutls_get_address .../emutls.c:392
      #1 ... in __sanitizer::BufferedStackTrace::UnwindImpl(...)
  SUMMARY: AddressSanitizer: stack-overflow ... in __emutls_get_address
  ```
  在 `version`/`index` 子命令上均复现。
- 隔离实验:同一源码树 `make mimalloc=0` 重建后 version/index/map
  全部正常(`./minibwa version` → `0.7-r421`)。
- 结论:mimalloc malloc override × OHOS emutls 是真根因,非 OHOS
  平台 bug。E210 知识(mimalloc MI_OVERRIDE 与 OHOS 内存管理机制冲突)
  覆盖此模式;本例进一步定位到崩溃点为 emutls bootstrap 内的递归。

## 源码修改

无补丁。所有适配通过 Makefile 命令行变量完成(CC/AR/ARCH/INCLUDES/
LDFLAGS/gpl/mimalloc 均为上游 Makefile 原生支持的开关)。

## 依赖版本

- zlib/1.3.1.1 (Conan, 静态)
- OHOS SDK clang 15.0.4, llvm-ar, lld
- pthread, m (系统)

## 验证结果

上游官方测试(README 流程 + api-test,详见 manifest upstream_tests):

```bash
$ ./minibwa version
0.7-r421
$ ./minibwa index test/chrM-human.fa.gz chrM-human   # exit 0
$ ./minibwa map chrM-human test/chrM-read_1.fa.gz test/chrM-read_2.fa.gz > aln.sam
# MAP_EXIT=0, SAM 非注释行 2013(2000 primary + 13 supplementary)
$ ./minibwa map --meth methM test/chrM-read_1.fa.gz test/chrM-read_2.fa.gz
# 甲基化模式 exit 0, 2013 行
# API 测试(上游 api-test 原样程序,链接包内 libminibwa.a):
$ clang -std=gnu99 -O2 -I<pkg>/include/minibwa ex-one.c <pkg>/lib/libminibwa.a -lz -lm -lpthread
$ ./mbmap-sgl chrM-human test/chrM-read_1.fa.gz   # exit 0, 1006 行 PAF
$ ./mbmap-batch chrM-human r1.fa.gz r2.fa.gz      # exit 0, 1006 行 PAF
# ex-one 与 ex-batch 输出逐字节一致(cmp 通过)
```

实测数据(与本机原生构建一致):
- paired-end map SAM 非注释行 **2013**(2000 primary + 13 supplementary;
  其中 5 条 mate-unmapped 记录无 NM tag,SAM 规范允许);
- api-test PAF 各 **1006** 行(1000 reads,6 条多 hit);
- 单端 map(read_1 only)SAM 1006 行。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/minibwa | CLI 二进制(已 .codesign 自签名) |
| lib/minibwa.a → libminibwa.a | 静态库(文档化 C API) |
| include/minibwa/minibwa.h | 公共 API 头 |
| licenses/LICENSE.txt | MIT 许可证 |

## 注意事项

1. **shared 不支持**: 上游 Makefile 只产 libminibwa.a,无 shared 目标,
   库代码无版本化符号,不伪造 .so——recipe 在 validate() 中显式拒绝
   shared 请求(package_type=application 本身无 shared 选项)。
2. **mimalloc 必须关**: OHOS 上 mimalloc override 必崩(见上表),
   recipe 默认 with_mimalloc=False 且 validate 拒绝 True;Linux 上
   可用 `-o with_mimalloc=True` 恢复上游默认分配器。
3. **GPL 组件默认启用**: 上游默认 `gpl=1`(QSufSort/bwtgen,IS 索引
   构造路径的一部分),minibwa 整体 MIT 但含此 GPL 组件;`gpl=0`
   可选(仅 libsais 索引)。默认跟随上游。
4. **测试数据随源码分发**: test/chrM-*.fa.gz 来自上游 tarball,
   test_package 复用包内 share/minibwa/test 数据,不重新下载。
