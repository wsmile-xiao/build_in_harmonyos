# libb64 1.2.1 适配笔记

## 编译环境
- 构建系统: makefile（上游简单 Makefile，非 autotools，无 configure 脚本）
- 编译日期: 2026-08-24
- 编译器: clang 15（OHOS toolchain，`/data/service/hnp/bin/clang`）
- 归档工具: llvm-ar
- 平台: OpenHarmony aarch64 (musl libc)
- 状态: built

## 源码调查（三方交叉验证，未猜测）

| 项 | 值 | 来源 |
|----|----|------|
| 官方主页 | https://libb64.sourceforge.net/ | SourceForge 项目页 |
| 下载 URL | https://downloads.sourceforge.net/project/libb64/libb64/libb64/libb64-1.2.1.zip | Homebrew Formula/lib/libb64.rb + Gentoo dev-libs/libb64 ebuild |
| sha256 | 20106f0ba95cfd9c35a13c71206643e3fb3e46512df3e2efb2fdbf87116314b2 | 实测下载计算 + Homebrew + Gentoo Manifest 三方一致 |
| 大小 | 23316 bytes | 实测 |
| 许可证 | CC-PDDC（公有领域） | 上游 LICENSE 文件 + Homebrew |
| 目录结构 | include/b64/{cencode,cdecode,encode,decode}.h + src/{cencode,cdecode}.c + base64/ + examples/ | 解压实测 |

### 公开 C API（从 include/b64/cencode.h / cdecode.h 真实头文件确认）

```c
/* cencode.h */
void base64_init_encodestate(base64_encodestate* state_in);
char base64_encode_value(char value_in);
int  base64_encode_block(const char* plaintext_in, int length_in, char* code_out, base64_encodestate* state_in);
int  base64_encode_blockend(char* code_out, base64_encodestate* state_in);

/* cdecode.h */
void base64_init_decodestate(base64_decodestate* state_in);
int  base64_decode_value(char value_in);
int  base64_decode_block(const char* code_in, const int length_in, char* plaintext_out, base64_decodestate* state_in);
```

> 注意：解码侧无 `base64_decode_blockend`（上游 c-example1.c 注释明确说明）。

## 上游测试核验（严格审计，未猜测）

### 1. 官方源码完整结构（解压 sha256-verified zip 实测）

```
libb64-1.2.1/            26 文件 / 7 目录
├── AUTHORS  ChangeLog  INSTALL  LICENSE  README
├── Makefile             # all: all_src all_base64 all_examples
├── include/b64/
│   ├── cencode.h        # C encode API（公开）
│   ├── cdecode.h        # C decode API（公开）
│   ├── encode.h         # C++ 包装
│   └── decode.h         # C++ 包装
├── src/
│   ├── cencode.c        # 唯一 encode 实现
│   ├── cdecode.c        # 唯一 decode 实现
│   └── Makefile
├── examples/
│   ├── c-example1.c     # 硬编码 "hello world" encode->decode 断言
│   ├── c-example2.c     # stdin→3 文件 encode/decode
│   └── Makefile         # BINARIES = c-example1 c-example2
└── base64/
    ├── base64.c         # 独立 base64 命令行工具
    └── Makefile         # BINARIES = base64
```

### 2. 正式自动化测试：不存在（全树搜索实证）

| 搜索项 | 结果 |
|--------|------|
| `test/` `tests/` 目录 | 不存在 |
| `make check` / `make test` 目标 | 4 个 Makefile 全部不含 check/test/ctest 目标 |
| CMakeLists.txt / CTestTestfile.cmake | 不存在 |
| configure / Makefile.am / configure.ac / meson.build | 不存在 |
| 文件名含 test 的源文件 (`test*.c` `*_test.c`) | 不存在 |

**结论：上游正式自动化测试 = 0（既无测试源文件，也无测试目标）。仅存在 examples/ 下 2 个示例程序。**

### 3. 上游 examples 实际编译与运行（OHOS aarch64 toolchain）

用 OHOS toolchain（clang 15 + llvm-ar）先编译 `src/{cencode,cdecode}.c` 归档为 `libb64.a`，再编译 2 个 example 并运行：

| example | 编译 | 运行 | 结果 |
|---------|------|------|------|
| `c-example1.c` | ✅ OK | ❌ **崩溃** | `Assertion failed: strcmp(input, decoded) == 0` → Signal 6 (core dumped) |
| `c-example2.c` | ✅ OK | ✅ exit 0 | 但解码输出文件 **12 字节 ≠ 输入 11 字节**，多余尾字节 `0x3e` (`>`) |

**关键发现：上游自带的官方 example `c-example1.c` 在 HarmonyOS PC 环境运行时直接崩溃**，原因是它的 decode 断言用 `strcmp(input, decoded)`，而 libb64 流式解码器返回的长度比真实明文多 1 字节。

### 4. decode padding 行为的根因（源码实证）

`src/cdecode.c` 中 `base64_decode_block` 的字符分派表将 `=` 映射到 **skip 分支**（与空白符同等处理），不作为终止符。`=` 不携带任何数据位，仅是长度提示，但流式解码器忽略它，从残余的部分位产生 1 个多余尾字节。

实测矩阵（4 个用例，OHOS toolchain 编译运行）：

| 明文 | 长度 | 编码 | `'='` 数 | decode cnt | diff | 尾字节 |
|------|------|------|---------|-----------|------|--------|
| `Hello, libb64!` | 14 | `SGVsbG8sIGxpYmI2NCE=` | 1 | 15 | +1 | `0x3e '>'` |
| `hello world` | 11 | `aGVsbG8gd29ybGQ=` | 1 | 12 | +1 | `0x3e '>'` |
| `abcdefghijkl` | 12 | `YWJjZGVmZ2hpamts` | 0 | 12 | 0 | 无 |
| `abcdefghij` | 10 | `YWJjZGVmZ2hpam==` | 2 | 11 | +1 | `0x3e '>'` |

**结论：多余尾字节是 libb64 流式 API 的真实行为（padding 存在时 cnt = ptlen + 1），不是 test_package bug。** 上游 README 未文档化调用者须用已知长度处理 decode，但上游 c-example1.c 的崩溃证明其示例代码本身也因未处理此行为而失败。

### 5. 严格长度正确解码的达成方式（实证）

`'='` 不携带数据位，strip 掉 `'='` 后再 decode 可得严格 `cnt == ptlen` + 逐字节一致：

| 变体 | decode cnt | diff | exact |
|------|-----------|------|-------|
| A（保留 `'=`） | 15 | +1 | no（多余 `0x3e`） |
| B（strip `'='`） | **14** | **0** | **YES** |

**test_package 据此设计为两条明确分开的路径**（不再把 padded 输入冒充为"strict decode PASS"）：
- **Path A（padded 原始输入行为验证）**：对 `SGVsbG8sIGxpYmI2NCE=` 直接调用原始公开 decode API，**不** strip `'='`，真实记录返回长度（cnt=15 ≠ ptlen=14）并断言其为已知非严格上游行为，确保 padding/skip 路径被真实覆盖，不掩盖上游缺陷。上游源码未修改。
- **Path B（strict round-trip using padding-stripped input）**：从编码结果复制工作缓冲区，strip 末尾 `'='` padding，调用原始 `base64_decode_block`，强制 `cnt == ptlen` + `memcmp` 逐字节一致。

两条路径分别达成：padded 原始路径被真实记录（不冒充正确标准 padding 行为），strict round-trip 长度严格一致。

## 编译方式

上游 `src/Makefile` 硬编码 `LINK.o = gcc`、`CFLAGS += -Werror -pedantic`、`$(AR) $(ARFLAGS)`，且默认 `CFLAGS += -O3`，不适合 OpenHarmony 交叉编译（`-Werror` 在不同 clang 版本下易误伤，`gcc` 在 OHOS 上不存在）。

**本次不打补丁、不修改任何上游源码**。conanfile.py 的 `build()` 直接：
1. 从 `tools.build:compiler_executables` 读取 OHOS clang（R33：不从 shell env 取）；
2. 用该 clang 编译两个真实上游源文件 `src/cencode.c`、`src/cdecode.c`（`-Iinclude -O2 -fPIC`）；
3. 用 `llvm-ar rcs` 归档为 `libb64.a`。

`package()` 拷贝 `lib/libb64.a` 与 `include/b64/*.h`（仅 C 公共头，C++ 包装器 encode.h/decode.h 也一并拷贝以保持头文件完整性）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile 不适合交叉编译 | 硬编码 gcc/ar + -Werror -pedantic | 不打补丁，conanfile.py 直接调用 OHOS toolchain 编译真实 C 源文件 |
| 2 | 上游无 make check/test 目标 | demo/库类软件，仅 examples/ 下示例 | test_package 编写真实功能测试（链接库 + 编码校验 + 解码校验 + 往返校验） |
| 3 | base64_encode_blockend 输出尾部换行 | libb64 设计行为 | 测试中 trim 尾部 `\n` 后再与期望值比对 |
| 4 | conanfile.py 不应裸用 ${CC}/${AR} | R33 铁律 | 用 `self.conf.get("tools.build:compiler_executables", check_type=dict)` 取编译器，`AR` 取自同 conf 或 env（仅在 self.run 命令字符串内使用，非 shell 变量插值） |

## 源码修改

**无**。本次适配未修改任何上游源码，也未应用任何补丁（`patches_applied: []`）。
仅通过 conanfile.py 在构建阶段绕过上游 Makefile，直接调用 OHOS toolchain 编译原始 `src/cencode.c` / `src/cdecode.c`。

## 依赖版本

无外部依赖。libb64 是纯 ANSI C 库，编译和运行仅依赖：
- musl libc（系统自带）
- clang 15（OHOS toolchain）
- llvm-ar（归档静态库）

## 测试说明

test_package/test_b64.c 是**真实功能测试**（非 include-only），解码侧分两条明确分开的路径：
1. 链接 `libb64.a`，调用真实 `base64_encode_block` / `base64_encode_blockend` 编码固定字符串 `"Hello, libb64!"`；
2. 校验编码结果等于独立计算的 `SGVsbG8sIGxpYmI2NCE=`（`printf 'Hello, libb64!' | base64`）；
3. **Path A（padded 原始输入行为验证）**：对 `SGVsbG8sIGxpYmI2NCE=` 直接调用原始公开 decode API，**不** strip `'='`，真实记录返回长度并断言其为已知非严格上游行为（cnt≠ptlen），确保 padding/skip 路径被真实覆盖、不掩盖上游缺陷；
4. **Path B（strict round-trip using padding-stripped input）**：从编码结果复制工作缓冲区，strip 末尾 `'='` padding，调用原始 `base64_decode_block`，强制 `cnt == ptlen` + `memcmp` 逐字节一致；
5. 额外做编码长度（4 的倍数）校验。

## 交付物

| 文件 | 说明 |
|------|------|
| conandata.yml | 源码 URL + sha256（无 patches 段） |
| conanfile.py | 直接调用 OHOS toolchain 编译，无补丁 |
| test_package/test_b64.c | 真实 encode/decode 功能测试（4 项断言） |
| test_package/conanfile.py | 编译并运行 test_b64 |
| test_package/MANIFEST.yml | 上游测试声明（上游无自动化测试套件） |
| manifest.yaml | 版本级编译元数据 |
| notes.md | 本笔记 |
