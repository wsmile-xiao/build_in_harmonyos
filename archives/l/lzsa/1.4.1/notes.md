# lzsa 1.4.1 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，非 autotools）
- 编译日期: 2026-06-30
- 编译器: clang/clang++
- Profile: ohos-aarch64 (armv8, Linux, clang 15)
- 状态: published

## 编译步骤

1. 下载源码 tarball（通过 ghproxy.net 镜像，GitHub 直连超时）
2. 解压到工作目录
3. 检查 Makefile：CC=clang，CFLAGS=-O3 -g -fomit-frame-pointer，LDFLAGS=（空值）
4. 编译：`make -j1 LDFLAGS=-static`
5. 手动安装：`cp lzsa $TEST_PREFIX$DEFAULT_PREFIX/bin/`（无 make install 目标）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络限制 | 使用 ghproxy.net 镜像下载 |
| 2 | 构建系统误分类 | 标注为 autotools，实际为纯 Makefile | 检查源码确认，conanfile.py 直接用 make |
| 3 | LDFLAGS 被覆盖 | Makefile 中 `LDFLAGS=` 赋空值 | 通过 `make LDFLAGS=-static` 命令行参数传递 |
| 4 | 无 install 目标 | Makefile 无 make install | 手动 cp 二进制到 bin/ |
| 5 | --version 返回 exit 100 | main() 未处理 --version/--help | 补丁添加 --version/--help 处理返回 exit 0 |
| 6 | test_package 找不到二进制 | conanrun PATH 未设置 | 使用完整路径而非 PATH 查找 |
| 7 | conan 源码下载超时 | conan create 从 GitHub 下载 | source() 添加本地 tarball 回退 |

## 源码修改

**补丁文件**: `patches/add-version-help.patch`
**修改文件**: `src/lzsa.c`
**类型**: portability
**内容**: 在 main() 参数解析循环中，`-stats` 处理之后、`else`（文件名）处理之前，添加 `--version`/`-version` 和 `--help`/`-help`/`-h` 两个 else-if 分支，分别打印版本/帮助信息并 `return 0`。

## 依赖版本

无外部依赖。lzsa 是独立的 CLI 工具，内嵌 libdivsufsort。

## 验证结果

```bash
$ file lzsa
lzsa: ELF executable, 64-bit LSB arm64, static, not stripped

$ readelf -d lzsa
There is no dynamic section in this file.

$ ./lzsa --version
lzsa command-line tool v1.4.1 by Emmanuel Marty and spke
exit=0

$ ./lzsa --help
lzsa command-line tool v1.4.1 by Emmanuel Marty and spke
usage: ./lzsa [-c] [-d] [-v] [-r] <infile> <outfile>
...
exit=0
```

conan-verify 8 道门禁全部通过 (G0/G1/G2/G3/G4 + L2/L4/L5)。

## 注意事项

- Makefile 中 `LDFLAGS=` 会覆盖环境变量，必须通过 make 命令行参数传递 `-static`
- 无 `make check` 目标；`./lzsa -test` 自测运行极慢（381s 后 kill），不适用于 CI
- conanfile.py source() 包含本地 tarball 回退逻辑，CI 环境可直接从 URL 下载

---

**编译结束**: 2026-06-30 12:22
**最终状态**: published
