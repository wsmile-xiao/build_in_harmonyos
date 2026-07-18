# FASTGA 1.5 OpenHarmony 适配笔记

## 构建环境

- 构建系统：普通 Makefile（框架初始误判为 autotools）
- 平台：OpenHarmony aarch64，clang 15
- 状态：built

## 构建与打包

使用 Conan 工具链提供的 `CC`/`CFLAGS`，追加上游警告选项及 Conan zlib 的 include/lib 路径后执行 `make -j1`。Makefile 的 `ALL` 变量包含 25 个程序，配方逐一复制到 package `bin/`，避免遗漏。

## 问题与解决方案

| 问题 | 根因 | 解决方案 |
|---|---|---|
| `ld.lld: undefined symbol: rindex` | OpenHarmony libc 不提供历史 BSD `rindex()` | 9 个源码文件中的 17 处调用替换为标准 C `strrchr()` |
| ONE schema 临时文件报 errno 30 | `ONElib.c` 硬编码只读 `/tmp` | 使用 `$TMPDIR`，未设置时回退当前目录（E002） |
| 官方 `HAP1.fasta.gz` 转换结束后 SIGSEGV | `Create_GDB()` 将调用者栈上的 `GDB` 交给 `ANO`，但未设置 `ano->shared`；`Free_ANO()` 因未初始化的所有权标志再次关闭并 `free(ano->gdb)` | 构造掩码 ANO 时明确设置 `ano->shared = 1`，由调用者继续负责 `Close_GDB()`；test_package 用含小写掩码的确定 FASTA 覆盖该清理路径 |
| 无 `make check` | v1.5 上游 Makefile未定义测试目标 | MANIFEST 声明豁免，test_package 实质执行 packaged `FAtoGDB` 并校验非空 `.1gdb`/`.bps` |

## 依赖

- `zlib/1.3.1`：通过 `conan download --only-recipe` 确认已发布
- pthread、libm：系统库

## 源码校验

官方 tarball SHA256：`c12e8f54ff69f76e872a8878a5a2e68c4a7bce18f91e246d2e06b21871477a0e`
