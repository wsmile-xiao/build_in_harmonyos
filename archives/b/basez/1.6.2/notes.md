# basez 1.6.2 适配笔记

## 概述

basez 是一个 base16/base32/base64 编码/解码命令行工具，实现了 RFC 4648 中定义的所有编码格式。

- 主页: https://codeberg.org/vonshedknocker/basez
- 作者: Milan Kupcevic
- 许可证: GPL-3.0-or-later
- 源码: 纯 C，4个源文件 (basez.c, base16.c, base32.c, base64.c)
- 依赖: 无外部依赖（仅 libc）

## 构建系统分析

basez 使用**自定义 configure 脚本**（非 autotools 生成），配合 `Makefile.src` 模板：

```
configure → 生成 Makefile (从 Makefile.src 替换 @MACROS@)
          → 生成 config.h (从 config.h.in 替换 _PLACEHOLDERS_)
          → 生成 configure.options (变量定义文件)
          → 生成 regtest.sh (从 regtest.sh.in 替换)
```

configure 特性:
- 接受 `CC=`, `CFLAGS=`, `CPPFLAGS=`, `LDFLAGS=` 作为命令行参数
- 编译器检测: `setexec CC gcc clang cc` (尝试依次查找)
- 默认 CFLAGS: `-O3`
- 平台检测: 编译并运行测试程序检测 LFS、符号链接等支持

## 编译步骤（前置适配方，未真机验证）

### 1. 下载源码
```
URL: https://deb.debian.org/debian/pool/main/b/basez/basez_1.6.2.orig.tar.gz
SHA256: 2a9f821488791c2763ef0120c75c43dc83dd16567b7c416f30331889fd598937
```
注: Debian mirror 提供上游原始 tarball（与 Codeberg v1.6.2 release 内容一致）。

### 2. configure
```bash
sh ./configure CC=clang --prefix=$DEFAULT_PREFIX
```

### 3. 编译
```bash
make -j1
```
产物: `basez` (ELF 可执行文件)

### 4. 上游测试
```bash
make test
```
运行 regtest.sh，测试 18 个 test 文件覆盖:
- base16 encode/decode/invalid
- base32plain encode/decode/invalid
- base32hex encode/decode/invalid
- base64plain encode/decode/invalid
- base64url encode/decode/invalid
- base64mime encode/decode/invalid

### 5. 安装（手动方式）
```bash
cp basez $PACKAGE/bin/
cp basez.1 $PACKAGE/share/man/man1/
```

## 适配说明

### 无需补丁

basez 1.6.2 的构建系统已经是 POSIX 兼容的，configure 脚本接受 CC= 和 --prefix=，
不需要修改源码即可在 OHOS 上构建。

### 待验证项

1. **编译器检测**: configure 使用 `setexec CC gcc clang cc`，在 OHOS 上需要确认
   clang 在 PATH 中可找到（通过 Conan 工具链注入）。
2. **ELF 签名**: OHOS 要求二进制签名才能执行，conanfile.py 已内置签名逻辑。
3. **符号链接**: 上游 `make install` 创建 base16/hex/base32plain 等符号链接指向 basez。
   当前适配仅复制 basez 二进制，符号链接待真机验证后添加。
4. **regtest 临时符号链接**: 测试脚本在构建目录创建临时符号链接 (base16 -> basez)，
   使用安全模式 (`[ -e X ] || ln -s`)，R5 合规。
5. **help2man**: 上游 `make install` 依赖 help2man 生成 man page。源码已包含
   预生成的 basez.1，手动复制即可绕过。

### 源码结构

```
basez.c   - 主程序（命令行解析、编排）
base16.c  - Base16 (hex) 编码/解码
base32.c  - Base32 (plain + hex variant) 编码/解码
base64.c  - Base64 (plain + url + mime + pem) 编码/解码
basez.h   - 头文件（编码/解码函数声明）
config.h.in - 配置头文件模板
Makefile.src - Makefile 模板
configure - 自定义 configure 脚本
regtest.sh.in - 回归测试脚本模板
tests/    - 18个测试数据文件
```

## 依赖版本

无外部依赖（纯 C 实现，仅依赖 libc）

## 交接说明

- **issue**: 待补（项目内未找到明确 issue 编号）
- **分支**: `feat/basez-1.6.2`
- **真机验证**: 未执行（本机前置适配方已完成，等待真机窗口）
- **阻塞点**: 无（basez 无外部依赖，构建系统简单）

### 真机验证命令

```bash
CI_PACKAGES="archives/b/basez/1.6.2" zsh ci/conan/build_and_test.sh
```

或在真机上:

```bash
conan create archives/b/basez/1.6.2/ \
    -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
```

### shadow CI 验证

```bash
/path/to/run-ohos-shadow-ci.sh archives/b/basez/1.6.2
```

---

**适配日期**: 2026-08-21
**当前状态**: draft（前置适配方完成，待真机验证）
