# DRAFT-genann-1.1.1-make-cflags-march-native-override — 上游 Makefile CFLAGS 硬编码 `-march=native` 时 OHOS 交叉/CI 构建必须整体覆盖 CFLAGS

> Contributor: pc2-44 | Status: Draft | Updated: 2026-09-19
> Source: PR feat/genann-1.1.1 【知识库扩展】
> Gate: conan-verify G2 / W3 local CI

## 背景

genann 1.1.1（codeplea/genann，zlib License）是单文件 C99 神经网络库，
零外部依赖，仅 libm。上游 Makefile 无 configure、无库 install 目标，
CFLAGS 写死为：

```make
CFLAGS = -Wall -Wshadow -O3 -g -march=native -MMD
```

`-march=native` 面向**构建宿主机** CPU 特性展开。OHOS 交叉编译
（`--target=aarch64-linux-ohos`）下：

- host != target（典型 CI：x86_64 宿主 → arm64 target）时，clang 会报
  `unsupported option '-march=native' for target 'aarch64-linux-ohos'`
  或静默产出带 host 指令集特性的产物，构建失败或产物失真。
- host == target（本 arm64 OHOS 设备）时实测可编译通过
  （`clang --target=aarch64-linux-ohos -march=native -c genann.c` rc=0），
  **但这不能证明 CI 可复现**——CI 宿主架构不同，同一 Makefile 必然失败。

## 根因

上游 Makefile 把构建宿主相关的 `-march=native` 硬编码进 CFLAGS，且该库没有
configure 开关可以关闭它。对 Conan 配方而言，唯一干净的路径是**整体替换**
CFLAGS——而不是 `CFLAGS+=` 追加（追加会触发 GNU make 命令行变量优先级陷阱，
见 DRAFT-heatshrink-0.4.1-make-cflags-commandline-override）。

## 方案

配方：

1. `generate()` 用 `GnuToolchain(self)` 生成工具链（编译器来自
   `tools.build:compiler_executables` conf，R33 不裸用 shell 环境变量）；
2. `build()` 执行 `make -j1 test CC=<cc> CFLAGS="-Wall -Wshadow -O2 -fPIC"`
   —— 命令行整体覆盖上游 CFLAGS，去掉 `-march=native`/`-O3 -g`；
3. 无库 install 目标时 package() 自行 `ar rcs libgenann.a genann.o` 并
   复制 include/ + lib/ + licenses/（E097 手动安装模式）。

验证（genann 1.1.1 实测）：

```bash
make test CC=/data/service/hnp/bin/clang \
  CFLAGS="-Wall -Wshadow -O2 -fPIC --target=aarch64-linux-ohos \
  --sysroot=<ohos-sdk native sysroot>"
./test    # ALL TESTS PASSED (521586/521586), 13/13
conan create . --build=missing -pr:b default -pr:h ohos-aarch64   # G2 PASS
conan-verify genann 1.1.1                                          # G1-G4 PASS
```

## 适用边界 / 反例

- 适用：plain-Makefile 型 C/C++ 库，上游 CFLAGS 含 `-march=native`（或其它
  host 特性 flag：`-mtune=native`、`-mavx*`、`-mcpu=native` 等），无 configure 开关；
  OHOS/Linux 交叉编译、CI 复现场景。
- 反例：host==target 的纯本机构建可编译通过——不要被"本机编译过"误导；
  CI 宿主（通常 x86_64）会失败。上游已有开关可关（如 `--disable-native`）时
  应优先用开关而非整体替换。
- 与 heatshrink 草稿的关系：同属"raw-make CFLAGS 覆盖"域但触发不同——
  heatshrink 是 `CFLAGS+=` 命令行变量优先级陷阱；本条目是上游硬编码 host flag
  必须整体替换。二者可互作诊断交叉引用。
