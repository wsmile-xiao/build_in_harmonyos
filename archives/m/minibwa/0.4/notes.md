# minibwa 0.4 适配笔记

## 概况

- 上游：https://github.com/lh3/minibwa （tag `v0.4`，版本串 `0.4-r400`）
- 构建系统：裸 Makefile（无 configure、无 CMake、无 install 目标）
- 包类型：application（只产出 `minibwa` 可执行文件；`libminibwa.a` 为中间产物）
- 许可证：主体 MIT；`bwtgen.c` GPL-2.0-or-later、`QSufSort.c` 自定义许可（故 conanfile 标注 `MIT AND GPL-2.0-or-later`）
- 依赖：zlib（conan `zlib/1.3.1` 裸 ref）；OpenMP 运行时由 OHOS clang 工具链自带（`/usr/local/lib/libomp.so`，RUNPATH 已覆盖）
- 无补丁：仅命令行变量驱动构建，源码零改动

## 关键决策

### 1. `mimalloc=0`（真实必要修复，E210）

上游 Makefile 默认链接 `mimalloc.o`（`MALLOC_O`），经 `-DMI_MALLOC_OVERRIDE` 接管 malloc/free。
本机（OHOS PC aarch64）实证：默认构建的 `minibwa` 一运行即 SIGSEGV（`idx-exit=139`、
`map-exit=139`、`Signal 11 (core dumped)`），与知识库 E210 条目（mimalloc MI_OVERRIDE 在
鸿蒙上崩溃）完全一致。`mimalloc=0` 是上游 README 明确支持的开关，构建后 index/map/
api-test 全链路正常。**不是**屏蔽，是规避已知的运行时崩溃根因。

### 2. zlib 注入：INCLUDES + LDFLAGS（Makefile 语义实测）

- Makefile 中 `INCLUDES` 是唯一没有 `+=` 追加的变量，命令行传入不会被覆盖：
  头文件路径走 `make INCLUDES="-I<zlib>/include"`。
- 命令行 `CPPFLAGS` 会让 Makefile 内 `CPPFLAGS+=` 整体失效（丢 `-DLIBSAIS_OPENMP`/
  `-DHAVE_KALLOC`），**不可用**；`LIBS` 被上游固定为 `-lpthread -lz -lm`，亦不可覆盖。
- 库路径走命令行 `LDFLAGS="-L<zlib>/lib"`（Makefile 链接行含 `$(LDFLAGS)`）。
- api-test/Makefile 自己拼 CFLAGS（仅 `-I..`），zlib 路径须走其 `CFLAGS` 变量。

### 3. 不注入 `-fuse-ld`，跟随 clang 默认 linker

知识库草稿 DRAFT-cdb-20251021-hnp-clang15-no-bfd-linker 结论：OHOS clang 15 默认
`--target=aarch64-unknown-linux-ohos` 注入 `-Wl,--code-sign`，GNU ld（bfd）不认识该
选项；HNP 环境本就无 bfd linker。实测不传 `-fuse-ld` 时链接产物正常（OHOS 动态
可执行 ELF），故不注入。若在 PATH 前置了 GNU ld 的环境里手跑 make 才会踩坑。

### 4. 上游测试在 build() 内执行（upstream_test_in_build: true）

上游官方测试 = GitHub Actions build.yml：`make -j` + `make -C api-test`（编译
mbmap-one/mbmap-batch 两个消费者程序）。本配方在 build() 内：

1. `make -C api-test`（编译官方 api-test）；
2. 运行 `mbmap-one` 于上游自带 test/chrM 数据，断言输出 PAF 对齐（首行 chrM）；
3. 用打包前的二进制跑 `index`+`map` 官方快速开始流程，断言 SAM 记录 RNAME=chrM。

test_package 与 test.sh 再做消费者级冒烟（tiny 生成数据、确定性 100M/NM:i:0 断言）。

### 5. GPL 保留（gpl=1 默认）

仓库内 GPL 包先例众多（bwa 本身即 GPL-3.0-or-later 全功能发布），且 `gpl=0` 会砍掉
`genraw` 命令与低内存索引路径，属功能性阉割。保持上游默认 `gpl=1`，许可证如实标注。

## 已知限制

- minibwa 无 `--version` 选项（exit 1）；版本查询用 `minibwa version` 子命令（exit 0，
  输出 `0.4-r400`）。CI L2 烟雾门禁回落 `--help`（exit 0）可通过。
- 无参数调用 exit 0（打印 usage）；`minibwa badcmd` exit 1。
- 未打包 `libminibwa.a`/`minibwa.h`（application 包只发 bin/，与 bwa 先例一致）；
  消费者需要头文件时参考上游 `api-test/ex-one.c` 与 `minibwa.h`（上游不提供
  install，头文件非自包含——`minibwa.h` 内部 include 需同目录源码文件）。

## 验证记录（本机 OHOS PC aarch64）

- `make ... mimalloc=0`：成功，无警告错误
- `./minibwa index test/chrM-human.fa.gz`：exit 0
- `./minibwa map ... read_1 read_2`：exit 0，SAM 输出（@HD/@SQ 头 + 记录）
- `make -C api-test`：成功，mbmap-one/mbmap-batch 编译链接通过
- `./api-test/mbmap-one ...`：exit 0，PAF 输出（A00744... chrM），两次运行 byte-identical
- test.sh 全流程（--help/version/index/map/awk 断言）：PASS

## 复现命令

```sh
conan create . --build=missing \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64
```
