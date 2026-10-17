# libgmpada 1.6 适配笔记

## 编译环境
- 构建系统: **手写顶层 Makefile**（`.NOTPARALLEL:`；无 configure/CMake/meson/gprbuild）
- 编译日期: 2026-09-20
- 编译器: **GNAT 9.5.0（gcc-ada）+ gcc 9**（Ada 与 C 胶水同源），非 OHOS clang
- 状态: built（已在鸿蒙电脑原生 `conan create` 完整跑通：build → package → test_package 构建 → 消费者签名运行并断言）

## 关键前提：Ada 必须原生 OHOS 构建

ohpcd 中唯一的 Ada 工具链 `gcc-ada/9.5.0` 与装配 `as`/`ld` 的 `binutils/2.46.0`
**都只有 OHOS/armv8 制品**，没有 Linux x86_64 交叉版 → 本地 WSL 无法交叉编译 Ada。
CI/真机用的是原生两 profile：

```
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方 `validate()` 对交叉构建显式拒绝。

## 为什么是静态绑定（shared=False）

`gcc-ada/9.5.0` 只交付 **非 PIC 的静态 Ada 运行时**（`adalib/libgnat.a`、`libgnarl.a`）。
把它链进上游的共享库会直接失败（真机实测原文）：

```
libgnat.a(a-stream.o): relocation R_AARCH64_ADR_PREL_PG_HI21 against symbol
  ... can not be used when making a shared object; recompile with -fPIC
make: *** [Makefile:119: obj/libgmpada.so.2] Error 1
```

因此只产出 `libgmpada.a`（上游 `make install` 同时装 .a/.so，配方改为手工装包）。
消费者用自己的 GNAT 工具链链接 Ada 运行时。

## 上游源码
- URL: `http://nicolas.boulenguez.free.fr/libgmpada-1.6.tar.xz`
- sha256: `7691cb8fa8e146799590093868355aee7367efa875b9479cce9492476d902ac4`
  （与 Debian `libgmpada_1.6.orig.tar.xz` 逐字节相同）
- 解包顶层: `libgmpada-1.6/`

## 源 URL 例外登记（R39 / PF7 官方托管例外）

- 源 URL 是上游作者官方站 `http://nicolas.boulenguez.free.fr/libgmpada-1.6.tar.xz`。
- 该站**不支持 HTTPS**：`curl -I https://nicolas.boulenguez.free.fr/libgmpada-1.6.tar.xz`
  → `OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to nicolas.boulenguez.free.fr:443`（2026-09-20 实测）。
- 亦无可用权威 HTTPS 镜像：Debian 池 `libgmpada_1.6.orig.tar.xz` 与上游 tarball **逐字节相同**
  （sha256 `7691cb8f…2ac4`，`cmp` IDENTICAL），但 Debian 主机被 PF7 判为"下游重打包源"；
  `sources.debian.org` 该数据路径 404；salsa 仅有 Debian 打包树，非上游 orig。
- 据此按 PF7 口径登记**官方托管例外**，PR 创建时显式 `--no-preflight` 跳过 PF7；
  `conandata.yml` 仍写上游官方 URL + 真实 sha256（不含 `file://`、镜像前缀或第三方搬运源）。

## 编译步骤（配方内）

1. 预生成 `src/gmp-h.ads`（见下）
2. `make obj/libgmpada.a obj/gmpada.gpr`，命令行覆盖：

```
GNATMAKE=<gcc-ada>/bin/gnatmake
CC=<gcc-ada>/bin/gcc  CXX=<gcc-ada>/bin/gcc
LDLIBS="-L<gmp libdir> -lgmp -lgnarl"
CPPFLAGS="-I<gmp include dir>"
ADAFLAGS="<上游默认>"
LDFLAGS="<上游默认> -L<gcc-ada adalib>"
prefix=/
```

3. 上游 demo（静态）编译、签名、运行
4. `package()` 手工安装：`share/ada/adainclude/gmpada`、`lib/ada/adalib/gmpada`、
   `lib/libgmpada.a`、`share/gpr/gmpada.gpr`（.gpr 改写为相对路径 + `-lgmp`）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游默认 `CXX := g++-9` 不存在 | gcc-ada 以 `--enable-languages=c,ada` 构建，无 g++/libstdc++ | 命令行覆盖 `CC`/`CXX` 为 gcc-ada 的 `gcc` |
| 2 | `#include <gmp.h>` 找不到 | 未把 GMP 头目录交给编译器 | `CPPFLAGS=-I<gmp include>` |
| 3 | `--dump-ada-spec` 试图链接，`undefined reference to main` | gcc-ada 的驱动包装器把没有 `-c/-S/-E/-fsyntax-only` 的调用判定为链接 | dump 时加 `-fsyntax-only` |
| 4 | `sed: obj/*_gmp_h.ads: No such file or directory` | GCC 实际生成 `obj/gmp_h.ads`（`package gmp_h is`），既不匹配上游 glob `*_gmp_h.ads`，也不匹配 sed 规则 `.*_gmp_h` | 配方自己生成：dump 后先把 `package gmp_h is` 改名 `TMP_gmp_h`，再套用**未修改**的上游 `gmp-h.ads.sed`，输出 `src/gmp-h.ads`（上游目标因时间戳更新而跳过） |
| 5 | `ld: cannot find -lgnat` | 配方最初用 `self.version`(1.6) 拼 adalib 路径，而运行时目录按 **编译器版本 9.5.0** 命名 | 改为 glob `<gcc-ada>/lib/gcc/*/*/adalib` 并校验 `libgnat.a` 存在 |
| 6 | 共享库链接失败（见上） | libgnat.a 非 PIC | 只构建静态库；`validate()` 拒绝 `shared=True` |
| 7 | 上游 demo 运行 `Permission denied` | OHOS 拒绝执行未签名 ELF（E489/E517） | 链接后用 `llvm-objcopy + binary-sign-tool -selfSign 1` 显式签名再运行 |

## 依赖版本

- gmp/6.3.0（静态 PIC，纯 C）
- gcc-ada/9.5.0（GNAT，OHOS/armv8）
- binutils/2.46.0（as/ld，OHOS/armv8）

## 验证结果

### 鸿蒙电脑原生 `conan create`（hdc 3QC0124C20001776，2026-09-20）

```
conan create archives/l/libgmpada/1.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

- gcc-ada/9.5.0 / binutils/2.46.0 / gmp/6.3.0 均就绪
- 静态库 `obj/libgmpada.a` 构建成功
- 上游 `demo.adb` 静态版链接成功、签名后**实际运行**（`[upstream] demo-static/demo ran successfully`）
- test_package：Ada 消费者 `gnatmake` 编译链接 `BUILD_OK`；`binary-sign-tool` 签名
  （`add codesign section success` / `write code sign data success`）后运行，输出
  **`LIBA_GMPADA_CONSUMER_OK`**（`2**100` 精确值、负值 Image、整除/取余恒等式三条断言）
- 设备侧日志：`/storage/Users/currentUser/gmpada.log`

### 未执行项

- 上游 `make test` 的**动态库 demo** 路径未执行：OHOS 上 libgnat.a 非 PIC，无法产出 `libgmpada.so`。
  静态 demo 路径已完整执行。

### 上游测试清点与执行（R51 口径）

| 项 | 值 |
|---|---|
| 上游测试入口 | 顶层 `Makefile` 的 `make test` 目标 |
| 清点入口数 N | 2（同一 `demo.adb` 的两种链接变体：`demo-dynamic/demo`、`demo-static/demo`） |
| 实际执行 N′ | 1（`demo-static/demo`，43 条 `pragma Assert` 全过） |
| 未执行 | 1（`demo-dynamic/demo`） |
| 未执行原因 | gcc-ada 只交付非 PIC 静态 Ada 运行时，`libgmpada.so.2` 链接报 `relocation R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC`，动态变体无从构建 |
| 断言数 | 上游静态 demo 43 + test_package 消费者 3 = 46（见 `test_package/MANIFEST.yml: assertion_count: 46`） |

## 注意事项

- `lang-preflight` 会把本库**误判为 `c`**（枚举缺 ada、不统计 `.adb/.ads`），
  与 libncursesada 同一盲区，作为该"一类问题"的第二个实证。
- 本地 WSL 无法跑 W3（Ada 无交叉工具链）；W3 由鸿蒙电脑/CI 原生执行。
---

**编译结束**: 2026-09-20 21:36
**最终状态**: built
