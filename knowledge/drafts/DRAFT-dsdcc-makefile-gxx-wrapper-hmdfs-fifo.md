# OHOS 小型独立测试套件(Makefile 硬编码 g++/cc)运行方案

- **Draft**: DRAFT-dsdcc-makefile-gxx-wrapper-hmdfs-fifo
- **来源**: dsdcc 1.9.6 适配 (W3 / testfec 上游测试)
- **日期**: 2026-09-25

## 问题

HarmonyOS PC (OHOS) 工具链只有 `clang`/`clang++`(位于 /data/service/hnp/bin/),不存在
`g++`、`cc`、`c++`。上游许多小型库的独立测试目录(如 dsdcc 的 `testfec/`)使用直接
Makefile 驱动,规则里**硬编码 `g++`**,直接运行报:

```
make: g++: No such file or directory
make: *** [Makefile:43: fec.o] Error 127
```

此外,HMDFS 文件系统不支持 `make jobserver` 使用的 mkfifo,`make -jN`(N>1)会报:

```
make: jobserver mkfifo: /storage/Users/currentUser/tmp/GMfifo15508: Operation not permitted
```

## 根因

1. OHOS 工具链只有 LLVM/Clang,无 GCC 系命令名(g++/cc/c++)。
2. 上游独立测试 Makefile 普遍硬编码编译器名,不通过 $(CXX) 变量。
3. HMDFS 拒绝 mkfifo,make 并行 jobserver 无法创建命名管道。

## 方案

不改任何上游源码,在测试构建时用符号链接包装 + 单线程:

```bash
mkdir -p ~/tmp/bin
rm -f ~/tmp/bin/g++ && ln -s "$(which clang++)" ~/tmp/bin/g++
ln -sf "$(which clang++)" ~/tmp/bin/c++
ln -sf "$(which clang)"  ~/tmp/bin/cc
PATH=~/tmp/bin:$PATH make -j1
```

- `PATH` 前置使 `g++` 解析到 clang++(兼容 GNU 命令行基础参数)。
- `-j1` 关闭 jobserver,彻底规避 HMDFS mkfifo 限制。
- 测试产物为独立自检程序,逐一运行并记录退出码。

## 验证

dsdcc 1.9.6 `testfec/` 12 个自检用例(qr/golay20/23/24/hamming7/12/15/16/viterbi/
viterbi35/crc/pn)全部编译并运行通过(exit=0),全量通过率 12/12 (100%)。

## 适用边界

- 适用:任何在 OHOS 上运行的 Makefile 驱动的小型独立测试/自检套件(无 configure 阶段)。
- 不适用:autotools configure 项目(见 E053,用 `export CC=clang CXX=clang++`);
  CMake/ctest 项目(用 CMakeToolchain);依赖 mbelib/serialdv 等额外链接的用例。
- 反例:若测试链接系统库或要求 GNU 扩展头,clang++ 包装可能不够,需专项适配。

## 相关条目

- similar_to: E053 (autotools configure 缺 cc1plus → set CXX=clang++)
- 与 E292 的 jobserver mkfifo 特征相关但其方案面向大型 C++ 数据处理库分层迁移