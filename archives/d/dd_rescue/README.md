# dd_rescue

Kurt Garloff 的 dd_rescue —— 面向**数据恢复**的块复制工具。相比 `dd`，它在
读错误时不会中止，而是按块降级、继续把能读到的数据抢救出来，并把坏区位置记录下来。

## ⚠️ 注意与 GNU ddrescue 的区别

这两个项目**名字相近但不是同一个软件**，适配/使用前务必区分：

| | **本包**（dd_rescue）| GNU ddrescue（`archives/d/ddrescue`）|
|---|---|---|
| 上游 | https://www.garloff.de/kurt/linux/ddrescue/ | https://www.gnu.org/software/ddrescue/ |
| 作者 | Kurt Garloff | Antonio Diaz Diaz |
| 实现语言 | C | C++ |
| 产物 | `dd_rescue` + `libddr_*.so` 插件 | `ddrescue` + `ddrescuelog` |
| 插件体系 | ✅ `libddr_hash` / `libddr_null` / `libddr_crypt` / `libddr_lzo` / `libddr_lzma` | ❌ 无 |

## Description

`dd_rescue` 按块复制数据，遇到读错误可自动降级块大小并跳过坏区，因此常用于
从有坏道的磁盘上抢救数据。它也支持反向复制（`-r`）、稀疏文件处理、以及通过
`-L libddr_*.so` 挂载插件对数据流做哈希、加密、压缩等变换。

主要产物：

| 文件 | 说明 |
|------|------|
| `bin/dd_rescue` | 主程序 |
| `lib/libddr_hash.so` | 哈希/校验插件（`libddr_MD5.so` 为其符号链接）|
| `lib/libddr_null.so` | 空操作插件（透传，用于对照）|
| `lib/libddr_crypt.so` | AES 加解密插件 |

> 上游完整的插件集还包括 `libddr_lzo.so` / `libddr_lzma.so`（压缩），
> 需开启对应可选依赖（LZO / LZMA）才会构建。本仓库默认关闭这些可选依赖，
> 以保持零外部依赖。

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 1.99.22 | built | 2026-09-12 | autoconf + 手写 Makefile；`conan create` EXIT=0 |

## OHOS 适配要点

1. **无预生成 `configure`** —— 官方 tarball 只带 `configure.ac`，配方在
   `source()` 中执行 `autoheader` + `autoconf`（即上游 `autogen.sh` 的两步）。
2. **`configure` 的 `umask 077` 在 HMDFS 上致命** —— `(umask 077 && mktemp -d)` 建出的
   目录为 `drwx--S--- (2700)`，因 uid 与文件 owner 不同而不可写，导致
   `config.status: could not setup config headers machinery`。配方改为 `umask 022`。
3. **`Makefile` 硬赋值 `CC = gcc`** —— 会覆盖环境变量，须在 `make` 命令行显式传
   `CC=<clang 绝对路径>`。
4. **`OS=$(shell uname)` 门控 `fstrim.o`** —— OHOS 上 `uname` 返回 `HarmonyOS`，
   `ifeq ($(OS), Linux)` 静默不成立 → 缺 `fstrim.o` → 链接期
   `undefined symbol: fstrim`（编译期无感）。须传 `OS=Linux`。
5. **不调用 `make install`** —— OHOS 无 coreutils `install`，且上游
   `INSTASROOT = -o root -g root` 在非 root 下必然失败；由配方按 upstream 布局落盘。

## 依赖

**无外部依赖**（仅 libc + libdl）。本配方不启用任何可选组件：

| 上游可选组件 | 对应插件 | 本配方 |
|-------------|---------|--------|
| LZO | `libddr_lzo.so` | ❌ 未启用（保持零外部依赖）|
| LZMA | `libddr_lzma.so` | ❌ 未启用 |
| OpenSSL | `libddr_crypt.so` 的加速实现 | ❌ 未启用（`libddr_crypt.so` 仍构建，走内置 AES 实现）|
| xattr | 扩展属性支持 | ❌ 未启用 |

> 因此产物只有 `libddr_hash.so` / `libddr_null.so` / `libddr_crypt.so`。
> 若需 LZO/LZMA 插件，需先为其引入 conan 依赖（ohpcd 上 `lzo/2.10`、`xz_utils` 已可用）。

## Installation

```bash
conan create archives/d/dd_rescue/1.99.22 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 实跑上游测试（门控，默认关；10 个子套件）
conan create archives/d/dd_rescue/1.99.22 \
  -o 'dd_rescue/*:run_upstream_tests=True' --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
