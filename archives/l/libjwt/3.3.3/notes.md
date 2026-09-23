# libjwt 3.3.3 — OHOS 适配笔记

## 适配概述

libjwt 是 C 语言实现的 JSON Web Token 库（作者 Ben Collins / maClara, LLC），MPL-2.0。
上游使用 CMake 构建，产出共享库 + 静态库 + 4 个命令行工具。
本适配为**单补丁适配**（`patches/0001-cmake-fix-codegen-bash-c.patch`）：修复上游 CMakeLists 的 codegen
命令引号拆词 bug（详见「错误 5」）。除该补丁外，上游源码在 OHOS aarch64 上无需修改即可编译并通过全部测试。

- 源码：`https://github.com/benmcollins/libjwt/archive/refs/tags/v3.3.3.tar.gz`
- SHA256：`a562e5548a8e10ac6fcba64a5e6d326c15712211cb54d25242c15e8b3250b4f2`（本地重复下载两次一致）
- 主页/文档：`https://libjwt.io`（v3 文档站）；**旧文档入口 `https://libjwt.io/stable` 对应 v2.1.1，与 3.3.3 不符，勿用**

## 构建系统

CMake（上游 `cmake_minimum_required(VERSION 3.7...3.15)`，本机 cmake 4.1.2 可直接配置）。
上游 `add_compile_options(-Wall -Werror -Wextra -Wunused)`，clang 15.0.4 下无告警，构建干净。

配置期间会打印若干行 `System is unknown to cmake, create: Platform/HarmonyOS ...`——
这是 CMake 没有 HarmonyOS platform module 导致的提示（知识库 E092），
cmake 会继续使用默认分支，不影响构建与产物（无需像部分配方那样强制
`CMAKE_SYSTEM_NAME=Linux`，libjwt 没有依赖 `CMAKE_SYSTEM_NAME` 的平台分支）。

## 依赖（W0 已核验，全部已发布到 ohpcd）

上游 `CMakeLists.txt` 的依赖声明（`pkg_check_modules`）：

| 依赖 | 上游要求 | 性质 | 本适配取值 | 制品仓状态 |
|------|---------|------|-----------|-----------|
| jansson | >= 2.0 | REQUIRED（`WITH_JSON_C=OFF` 时） | `jansson/2.15.1.1` | 已发布 |
| openssl | >= 3.0.0 | REQUIRED | `openssl/3.5.6` | 已发布 |
| check | >= 0.9.10 | 仅测试（`WITH_TESTS=ON`） | `check/0.15.2`（`test_requires`） | 已发布 |
| gnutls | >= 3.6.0 | 可选（默认 ON=auto） | 关闭（`WITH_GNUTLS=OFF`） | `gnutls/3.8.10` 已发布，但不需要 |
| json-c / mbedcrypto / libcurl / kcapi | — | 可选（默认 OFF） | 关闭 | json-c 已发布；libcurl、mbedtls 未发布（不影响本包） |
| Doxygen | >= 1.9.8 | 可选（仅生成文档） | 未安装 → 跳过文档 | — |

> ⚠️ 注意：早期归档（`archives/l/libjwt/3.3.3/` 的历史存根）写的依赖是 `jansson/2.15.0`，
> 该版本**从未发布**到制品仓（`conan download jansson/2.15.0 -r=ohpcd` 失败，
> `archives/j/jansson/manifest.yaml` 记录的是未完成态）。本适配改用已发布的 `2.15.1.1`。

## 首个真实错误、根因分析与最小修改

### 错误 1（阻塞测试）：libcheck 无法创建 fork 通信临时文件

**真实报错（11 个套件全部命中，退出码 2）**：

```
/storage/Users/currentUser/.conan2/p/b/check01f6875eb3aa2/b/src/check_msg.c:317:
  Unable to create temporary file for communication; may not have permissions to do so
```

**根因**：`check-0.15.2/src/check_msg.c` 的临时目录选择优先级是

```
TEMP → P_tmpdir 宏 → TMPDIR → 当前目录
```

OHOS 的 libc 定义了 `P_tmpdir = "/tmp"`，而本设备 `/tmp` 是**只读 erofs**
（`touch /tmp/x` → `Read-only file system`）。因此：

- 只设 `TMPDIR` **无效**（优先级低于 `P_tmpdir`）；
- 只设 `CK_FORK=no` **也无效**（`check_msg.c` 在 `setup_pipe()` 中无条件建临时文件）。

用 `grep -a` 扫 `libcheck.a` / `libcheck.so` 可直接看到烘焙进去的字面量 `/tmp`，可复现定位。

**最小修改（不碰任何源码）**：把优先级最高的 `TEMP` 指向可写目录。
配方在 `_prepare_ohos_test_runtime()` 里把 `TEMP`/`TMPDIR`/`TMP` 统一钉到
构建目录下的 `hmbs-tmp`。修好后 `jwt_crypto` 立即从 rc=2 变为
`100%: Checks: 1, Failures: 0, Errors: 0`。

> 该问题与知识库既有 `check/0.15.2` 笔记中"上游测试套件需要创建临时文件，
> 在 OHOS /tmp 只读环境下会失败"是同一个坑；本适配补充了**为什么 `TMPDIR` 不够、
> 必须用 `TEMP`** 的精确机制。

### 错误 2（驱动方式）：上游 add_test() 硬编码 /bin/bash

**真实报错**：`ctest -N` 无法正确定位测试命令，`ctest` 无法驱动任何套件。
本机实测：`/bin/bash` **不存在**（`ls /bin/bash` → No such file or directory），
根文件系统只有 `/bin/sh`；bash 实际位于 `/data/service/hnp/bin/bash`（非 FHS 路径）。

上游 `CMakeLists.txt` L315-316 / L342 把解释器写死：

```cmake
add_test(NAME ${LibTest_NAME} COMMAND /bin/bash -c
    "export TEST=${LibTest_NAME}; . ${CMAKE_SOURCE_DIR}/tests/test-env.sh; exec ${CMAKE_BINARY_DIR}/tests/${LibTest_NAME}")
```

**最小修改（不碰源码、不使用 ctest）**：配方按 `add_test()` 的**等价语义**直接执行
测试二进制，并用 `/bin/sh`（`CONFIG_SHELL` 优先）来 source `tests/test-env.sh`：

```
export TEST=<suite>; . <src>/tests/test-env.sh; exec <build>/tests/<suite>
```

`tests/test-env.sh` 是纯 POSIX 语法，`/bin/sh` 可正常 source，语义与上游一致。
此改动不裁剪任何测试用例，11 个套件全部真实执行。

### 错误 3（副作用，自测发现）：进程环境泄漏到 test_package

第一次 `conan create` 时，test_package 的构建阶段出现：

```
make: jobserver mkfifo: <libjwt 构建目录>/hmbs-tmp/GMfifo2350: Operation not permitted
```

**根因**：conan 在**同一个 Python 进程**里接着执行 test_package；`build()` 里写进
`os.environ` 的 `TMPDIR` 残留下来，make 便把 jobserver fifo 建到了本包构建目录。
**修复**：把测试期环境改动包进 `try/finally` 还原（`TEMP`/`TMPDIR`/`TMP`/`LD_LIBRARY_PATH`）。
修复后 `conan create` 日志中该告警数归零。

### 错误 4（质量门禁 L5）：共享库缺 DT_SONAME；补上 SONAME flag 后又撞上版本化软链

**真实报错（W3 的 L5 门禁，2 处）**：

```
[fail] L5a: libjwt.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址
       文件: /lib/libjwt.so
[fail] L5c: 1 个 .cmake 文件含 IMPORTED_NO_SONAME TRUE — 下游必须按完整路径链接
```

**根因（两环，均已实测确认）**：

第一环：CMake 没有 `Modules/Platform/HarmonyOS.cmake`，所以
`CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG` 不会在 `Platform/Linux.cmake` 里被赋值。
而这个变量正是 `cmGeneratorTarget::HasSOName()` 的判据——它为空时链接期不发
`-Wl,-soname`，`libjwt.so` 就没有 `DT_SONAME`（L5a 失败），CMakeDeps 也据此生成
`IMPORTED_NO_SONAME TRUE`（L5c 失败）。

第二环：只补这个变量又会立刻启用 SONAME 语义——上游 `CMakeLists.txt` L221-223 对
`jwt` 目标声明了 `VERSION ${LIBJWT_VERSION_INFO}` / `SOVERSION ${LIBJWT_COMPATVERSION}`，
于是产物从「单个 `libjwt.so`」变成 `libjwt.so.14.2.7` ＋ `libjwt.so.14` ＋ `libjwt.so`
两级**版本化符号链接**；而这类软链在目标文件系统上创建/替换会失败
（实测 `cmake_symlink_library` 报 `failed to create symbolic link 'libjwt.so.14':
Permission denied`，链接步骤直接 Error 1）。

**最小修改（不碰源码，`generate()` 里三行）**：

```python
tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
```

`CMAKE_PLATFORM_NO_VERSIONED_SONAME` 是 CMake 的官方平台变量（语义即「本平台不采用
版本化 soname 命名」）。三行合起来让平台产出**单个实体 `libjwt.so` ＋ 可重定位
`DT_SONAME`**，实测结果：

```
$ readelf -d <pkg>/lib/libjwt.so | grep -E 'SONAME|NEEDED'
 0x0000000000000001 (NEEDED)   Shared library: [libjansson.so]
 0x0000000000000001 (NEEDED)   Shared library: [libc.so]
 0x000000000000000e (SONAME)   Library soname: [libjwt.so]
```

**与仓库既有先例一致**：`expat/2.8.4`、`libharu/2.3.0`、`attica/6.14.0` 等 9 个配方
用的正是这同一组三行；`archives/l/libevent/2.1.13/patches/0001-cmake-ohos-unversioned-shared-libraries.patch`
的注释原文也写着 *"HMDFS cannot reliably create or replace the versioned symlink
chain. Emit the public unversioned library as the real file."*。知识库 E492 要求
「软链被拒时回退为实体文件」，E505 记录 OHOS 加载器无法经软链别名解析——本适配选择在
**构建期**就不产生版本化别名，一次到位；SONAME 这个修复点本身无需补丁（仅 CMake 变量）。

## 上游测试结果（本机 OHOS aarch64 实测）

框架 libcheck（check/0.15.2），由上游 CMakeLists 的 `jwt_add_test()` 注册并执行：

| 套件 | 用例（Checks） | 失败 | 错误 | 结果 |
|------|---------------|------|------|------|
| jwt_crypto | 1 | 0 | 0 | PASS |
| jwt_jwks | 5 | 0 | 0 | PASS |
| jwt_jwks_errors | 4 | 0 | 0 | PASS |
| jwt_ec | 4 | 0 | 0 | PASS |
| jwt_rsa | 8 | 0 | 0 | PASS |
| jwt_hs | 4 | 0 | 0 | PASS |
| jwt_builder | 18 | 0 | 0 | PASS |
| jwt_checker | 30 | 0 | 0 | PASS |
| jwt_flipflop | 22 | 0 | 0 | PASS |
| jwt_claims | 5 | 0 | 0 | PASS |
| jwt_security | 46 | 0 | 0 | PASS |
| **合计** | **147** | **0** | **0** | **11/11 PASS** |

未注册套件（如实申报）：`tests/jwt-cli.bats` 共 9 个 bats 用例。镜像内无 `bats`，
上游用 `find_program(bats)` 探测、探测不到即不注册该测试——这是**上游自身的优雅降级**，
非本配方裁剪；CMAKE 配置阶段 `BATS_CMD` 为空，不会注册 `jwt_cli` 测试。

test_package（消费者视角）：
- `test.c`（12 项检查）：JWKS 载入 → 取 JWK → HS256 签发 → 校验通过 →
  篡改后校验失败（负样本），12/12 Passed。
- `test_ohos.c`（鸿蒙平台特有，9 项检查，test_package 合计 21/21 Passed）：
  dlopen("libjwt.so") 验证加载器按裸 SONAME 解析（OHOS musl 无法经版本化
  软链别名解析，E505）；dlsym/dladdr 验证符号可达且加载路径为无版本后缀
  实体文件；直接解析 ELF `.dynamic` 段验证 `DT_SONAME == "libjwt.so"`
  （错误 4 修复的运行时证据）、`DT_NEEDED` 含 libjansson.so 且不含
  libcrypto/libssl（OpenSSL 静态链入的运行时证据）；`/bin/sh` 存在可执行
  （错误 2 等价驱动解释器的环境前提）。
  ⚠️ libjwt v3 已移除 `jwt_new`（头文件仅存 `jwt_free_t` typedef），
  符号探测须用 `jwt_builder_new`。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/libjwt.so` | 共享库（对外主链接目标；上游 `libjwt.pc` 亦为 `-ljwt`） |
| `lib/libjwt.a` | 静态库（上游无条件同时构建；两者 OUTPUT_NAME 均为 `jwt`） |
| `bin/jwt-verify`、`bin/jwt-generate`、`bin/jwk2key`、`bin/key2jwk` | 4 个命令行工具（故软件级目录需 `commands.json`，R38） |
| `include/jwt.h`、`include/jwt_export.h` | 公开头文件 |
| `lib/pkgconfig/libjwt.pc`、`lib/cmake/LibJWT/`、`share/man/man1/*.1` | pkg-config / CMake / man 集成文件 |

`libjwt.so` 的动态依赖实测（`llvm-readelf -d`）：`libjansson.so` + `libc.so`。
**没有 libcrypto/libssl**——`openssl/3.5.6` 制品仓只提供静态库（`libcrypto.a`/`libssl.a`），
OpenSSL 被静态链入，因此运行时不引入 OpenSSL 动态库依赖。

另：本包**不产生任何版本化软链**（`libjwt.so.14 -> libjwt.so.14.2.7` 之类），
`libjwt.so` **带** `DT_SONAME=libjwt.so`（`readelf -d` 实测）。这是配方显式设置
`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` 的结果（见「错误 4」）：上游
`cmake/LibJWTVersions.cmake` 虽然算出了 `LIBJWT_VERSION_INFO=14.2.7` /
`LIBJWT_COMPATVERSION=14`，但 HarmonyOS 侧关闭了版本化命名，最终发布的是
**单个实体 `libjwt.so` ＋ 裸 SONAME**。因此知识库 E316/E492/E505 那类
「版本化别名是软链 → OHOS 加载器解析失败」的问题在本包不成立。

## 注意事项

1. **依赖制品仓的版本必须实测**：不要沿用归档里历史写的依赖版本，先
   `conan download <ref> -r=ohpcd --only-recipe` 验证（R35）。
2. **OpenSSL 静态链入**：若未来 `openssl` 制品仓改为同时提供动态库，`libjwt.so` 的
   运行时依赖会多出 `libcrypto.so`，需重新确认 OHOS 加载路径。
3. **上游测试与 `/bin/bash` 无关**：如果把 `WITH_TESTS` 关掉，构建会明显变快，
   但会丢失 147 个用例的回归证据；本适配选择保留并真实执行。
4. **test_requires 不污染下游**：`check/0.15.2` 仅用于本包编译期测试，
   不会出现在消费者的依赖图里。

## 错误 5（OHOS 特有问题，阻塞编译）：make jobserver 并行 spawn clang 静默失败

**现象**：`conan create` 里的 `cmake.build()`（conan 自动注入 `-j<cpu_count>` 并行）
在 OHOS 设备上稳定失败——make 报 `Error 1` 但**无任何编译器错误输出**（静默失败）。
失败点随并行调度**漂移**：首现于 codegen（jwt-builder.i/jwt-checker.i），修掉后
漂移到任意 `.c.obj`（jwt-memory.c.obj、jwt.c.obj、test.c.obj …）。

**根因（两层）**：
1. 上游 CMakeLists 的 codegen 命令写的是 `COMMAND bash -c "${CMAKE_C_COMPILER} -E ..."`
   ——`add_custom_command` 会对带引号的 COMMAND 做 separate_arguments 拆词，引号丢失后
   `bash -c` 只拿到裸编译器名（无 `-E` 及其余参数），**确定性失败**。已用 patch
   `patches/0001-cmake-fix-codegen-bash-c.patch` 改为直接 `${CMAKE_C_COMPILER} -E ...`。
2. **更底层**：即使命令正确，conan（musl 动态链接的 python）经 `self.run()`
   （`shell=True`）驱动 `cmake --build -jN`（N>1）时，make 的 jobserver 并行 spawn
   clang 子进程在 OHOS 内核/musl 进程树下**静默失败**。直接 `make -j1` /
   `subprocess` 执行同一命令 **100% 成功**，`make -j4` 稳定失败 → 是 jobserver
   并行竞态，与 codegen 无关。

**修复（在 conanfile 内彻底绕开 jobserver 并行）**：
- 主包 `build()`：不再用 `cmake.build()`（会注入 -jN），改 `subprocess.run(["make", "-j1"])`
  串行编译（绝对路径 `/data/service/hnp/bin/make`）；并先用 subprocess 预生成两个 `.i`
  文件跳过 make 的 codegen 步骤（双保险）。
- test_package `build()`：同样改 subprocess `make -j1`。
- 结论：本库编译量小（11 测试 + 2 库 + 4 工具），`-j1` 代价可忽略，换取确定性通过。

**验证**：`conan create` 全量 EXIT=0 —— 上游测试 11/11 套件 147 checks 全 PASS；
test_package 21/21（test_libjwt 12 + test_ohos 9，ohos_specific_tests=9）。

> ⚠️ 这是 OHOS 平台的通用陷阱：**任何 conan 配方若在 `conan create` 内因 make
> `Error 1` 静默失败且失败点漂移，优先怀疑 jobserver 并行竞态，改用 `-j1` 串行验证**。
> 建议沉淀到 knowledge/（musl 兼容 / error-patterns）。
---

## 错误 6（CI 环境问题，阻塞链接）：lld 加载不到正确的 libxml2.so.16

**现象**：本地 `conan create` 全过，但 CI 上 `Linking C shared library libjwt.so`
失败：

```
Error loading shared library libxml2.so.16: (needed by .../llvm/bin/lld)
Error relocating .../lld: xmlFreeDoc: symbol not found
...
clang-15: error: linker command failed
```

**根因**：OHOS SDK 的 lld 链接器动态链接 `libxml2.so.16`（interp 为 musl ld.so，
RUNPATH `$ORIGIN/../lib` 即 SDK 的 `llvm/lib`）。本配方用 `subprocess.run` 直接调
`make` 绕开了 conan 的 buildenv 激活，导致 profile `[buildenv]` 里声明的
`LD_LIBRARY_PATH=+(path).../llvm/lib` 没注入到 make 的链接子进程。本机 ambient 环境
恰好带了该路径所以能过，CI worker 上没有 → lld 加载不到（或加载到 ambient 里不兼容
的 libxml2.so.16 导致 `symbol not found`）。

**修复**：在 `_make_serial_build()`（主包）与 test_package `build()` 里，显式从
编译器路径推导 SDK `llvm/lib`（`realpath(cc)` 上溯两层 `/lib`），前置进
`subprocess` 的 `LD_LIBRARY_PATH`。与 knowledge E120/E132/E341 及 abr2gbr/abseil/
absl 同款先例一致。

**验证**：本地 `conan create` 仍 EXIT=0（21/21），待 CI 复跑确认。
---


**编译结束**: 2026-09-15 22:45
**最终状态**: built（21/21 测试全过，含 9 项 OHOS 特有测试）
---

**编译结束**: 2026-09-15 22:47
**最终状态**: built
