# libjwt3 3.3.3 适配笔记（OHOS aarch64）

> 记录本版本在 OpenHarmony PC（arm64）上的适配过程、实测结论与证据。
> 上游：https://github.com/benmcollins/libjwt  tag `v3.3.3`
> 归档：`archives/l/libjwt3/3.3.3/`

## 1. 任务与环境

| 项 | 值 |
|---|---|
| 包名/版本 | `libjwt3/3.3.3`（与同源 `libjwt`、`libjwt-tools`、2.x 线 `libjwt2` 并存，包名不同不冲突） |
| 设备 | HarmonyOS aarch64（Kernel 1.12.0），本机即目标平台，非交叉编译 |
| 编译器 | clang 15（`/data/service/hnp/bin/clang`，libc++） |
| conan | 2.29.1（OHOS 适配版，`os=OHOS` 为有效枚举） |
| profile | `ohos-aarch64`（os=OHOS / os.version=6.0 / arch=armv8 / clang15 / libc++ / cppstd17 / Release） |
| 构建系统 | CMake（`cmake_minimum_required 3.7...3.15`） |

## 2. W0 依赖预检（R36 / R35）

适配前先确认依赖已发布到 `ohpcd` 制品仓。**禁用 `conan list`** 判 binary 存在性
（cnb.cool 搜索 API 对 binary 返回不完整），故全部用 `conan download --only-recipe` 实测：

| 依赖 | 命令 | 结果 |
|---|---|---|
| jansson/2.15.1.1 | `conan download jansson/2.15.1.1 -r=ohpcd --only-recipe` | ✅ 命中（revision d5c4ca62…，2026-07-30） |
| openssl/3.5.6 | `conan download openssl/3.5.6 -r=ohpcd --only-recipe` | ✅ 命中（revision 748fc4de…，2026-07-12） |
| check/0.15.2 | `conan download check/0.15.2 -r=ohpcd --only-recipe` | ✅ 命中（revision 6d41c307…，2026-08-04） |

结论：三个依赖全部已发布，无需先适配依赖（R36 拓扑序无需触发）。

## 3. 构建系统分析（上游 CMakeLists 关键事实）

| 事实 | 位置 | 影响 |
|---|---|---|
| 依赖用 `pkg_check_modules()` 定位 | CMakeLists:36（jansson）、:71（openssl）、:296（check） | 配方必须启用 **PkgConfigDeps**；仅 CMakeDeps 不够 |
| `add_library(jwt SHARED)` + `add_library(jwt_static STATIC)`，两者 `OUTPUT_NAME jwt` | CMakeLists:74-78 | **无条件**同时产出动/静态库；`BUILD_SHARED_LIBS` 无任何分支，设了也无效 |
| `jwt_add_tool()` 定义在 `WITH_TESTS` 块之外，无条件构建，PRIVATE 链 `jwt_static` | CMakeLists:176-205 | build() 必须全量构建才能拿到 4 个 CLI 工具 |
| 依赖 `PkgConfig::OPENSSL` **PUBLIC** 链接 jwt / jwt_static | CMakeLists:165-166 | openssl 头文件路径会经 PUBLIC 传播 |
| `add_test(... COMMAND /bin/bash -c ...)` | CMakeLists:315 | OHOS 无 `/bin/bash` → ctest 不可用 |
| `find_program(BATS_CMD bats)` 探测不到即不注册 CLI 测试 | CMakeLists:297, 342 | 镜像无 bats → 上游自身不注册该测试 |
| `VERSION/SOVERSION` 来自 `cmake/LibJWTVersions.cmake`（SO_CRA 16:7:2） | CMakeLists:221-224 | 若不关版本化命名 → 产出 `libjwt.so.14`（HMDFS 上建符号链接失败） |
| 测试二进制输出目录 `<build>/tests`，工具输出 `<build>/tools` | CMakeLists:312, 188 | 产物定位依据 |

## 4. 源码补丁（1 个）

### 0001-cmake-fix-codegen-bash-c.patch

**问题**：上游 codegen（CMakeLists:86-96）用

```cmake
COMMAND bash -c "${CMAKE_C_COMPILER} -E -DJWT_BUILDER ... -o jwt-builder.i ${CMAKE_C_FLAGS}"
        -o jwt-builder.i
```

`add_custom_command` 的 COMMAND 参数按空格拆词，**引号在拆词后不再起保护作用** →
`bash -c` 只收到裸编译器名（如 `/data/.../clang`）作为脚本，无任何输入 →
clang 以 "no input files" 失败，且 **CMake 只报 `Error 1` 不显示任何编译器输出**（静默失败）。
`jwt-builder.i` / `jwt-checker.i` 是 `jwt-builder.c` / `jwt-checker.c` 用 `#include` 引入的，
生成失败即整体编译失败。

**修法**（POSIX/上游风格，无平台宏）：

```cmake
COMMAND ${CMAKE_C_COMPILER} -E -DJWT_BUILDER ${CMAKE_SOURCE_DIR}/libjwt/jwt-common.c ${CMAKE_C_FLAGS} -o jwt-builder.i
```

即去掉 `bash -c` 包装，直接调编译器（顺序调整为 `-o` 在末尾）。该修法对非鸿蒙平台**行为等价
且更正确**（不再依赖 shell 引号解析），符合 R8"对非鸿蒙平台透明"。

**验证**：对干净上游源码 `patch -p1 --dry-run` 通过；`conan create` 从 tar 包重建全链路通过。

> 本版本**无第二个源码补丁**：SONAME 缺口（见 §5）与 jobserver 并行（见 §6）均通过
> conanfile.py 变量/构建方式解决，不需要改源码。

## 5. SONAME 处理（R26 相关的平台缺口 · 不改源码）

**根因链**：CMake 无 `Modules/Platform/HarmonyOS.cmake`，故
`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 不会被赋值。而该变量正是
`cmGeneratorTarget::HasSOName()` 的判据，产生两个必须同时解决的后果：

1. 变量为空 → 链接期不发 `-soname` → `libjwt.so` **无 DT_SONAME**（L5a 门禁失败），
   且 CMakeDeps 生成 `IMPORTED_NO_SONAME TRUE`（L5c 失败）。
2. 只补该变量 → CMake 立即启用 SONAME 语义，上游声明的 `VERSION 14.2.7 / SOVERSION 14`
   生效 → 产物变成 `libjwt.so.14` + 两级版本化符号链接链，而 **HMDFS 上版本化符号链接
   无法创建/替换**（`cmake_symlink_library` 报 `failed to create symbolic link 'libjwt.so.14':
   Permission denied`，链接步骤 Error 1）。

**解法**（`generate()` 中三行，与 expat/2.8.4、libharu/2.3.0、attica/6.14.0 同款）：

```python
tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
```

产出「实体文件 `libjwt.so` + 可重定位裸 SONAME」，无版本化链接链。
依据：E330 / E383 / `knowledge/drafts/DRAFT-cmake-harmonyos-platform-soname-flag.md`。

## 6. OHOS 平台陷阱与对策

| # | 陷阱 | 现象 | 对策 |
|---|---|---|---|
| 1 | **/tmp 只读 + libcheck 临时目录优先级** | libcheck 优先级 `TEMP → P_tmpdir → TMPDIR → 当前目录`，OHOS libc 把 `P_tmpdir` 定义为只读 `/tmp`；只设 `TMPDIR` 时每套件在 `core_setup()` 前 abort：`Unable to create temporary file for communication` | `_prepare_ohos_test_runtime()` 把 **TEMP/TMPDIR/TMP** 全部钉到 `build_folder/hmbs-tmp`（TEMP 优先级最高） |
| 2 | **上游 add_test 硬编码 /bin/bash** | OHOS 根文件系统只有 `/bin/sh`（bash 在 `/data/service/hnp/bin/bash`）→ ctest 无法驱动 | 不使用 ctest，按 `add_test()` 等价语义直跑：`export TEST=<suite>; . <src>/tests/test-env.sh; exec <build>/tests/<suite>`（`_find_shell()` 依次取 `CONFIG_SHELL` → hnp bash → `/bin/sh`） |
| 3 | **make jobserver 并行 spawn 竞态** | conan `self.run()`（musl python + `shell=True`）驱动 `cmake --build -jN`（N>1）时 make jobserver 并行 spawn clang **静默失败**（Error 1 无输出，失败点随调度漂移） | 改 `subprocess` 直接 `make -j1` 串行编译（`_make_serial_build()`）；本库编译量小，代价可忽略。见 E525/E074 |
| 4 | **SDK lld 的 libxml2.so.16 依赖** | lld 动态依赖 SDK `llvm/lib/libxml2.so.16`；subprocess 绕过 conan buildenv → 链接报 `Error loading shared library libxml2.so.16` | `_sdk_llvm_libdir()` 由编译器 realpath 推导 `llvm/lib` 并前置进 `LD_LIBRARY_PATH`。见 E120/E341 |
| 5 | **测试二进制加载构建树 .so** | HOFS 加载器不依赖二进制内嵌 DT_RPATH（E505） | `_prepare_ohos_test_runtime()` 把 tests 目录、build 目录与各依赖 libdir 放进 `LD_LIBRARY_PATH` |
| 6 | **进程环境残留污染 test_package** | conan 在同进程接着跑 test_package，残留 `TMPDIR` 会让后续 make 把 jobserver fifo 建到本包构建目录 → `make: jobserver mkfifo ... Operation not permitted` | `_run_upstream_tests()` 用 `try/finally` 保存并还原 `TEMP/TMPDIR/TMP/LD_LIBRARY_PATH` |

## 7. R26 系统同名库检查

```bash
find /lib /lib64 /usr/lib /usr/lib64 /system/lib /system/lib64 -maxdepth 3 -name "libjwt.so*"
# → 无命中；libjwt.a 同样无命中
```

结论：`libjwt.so` **不是**系统同名库 → 按 R26 **保持默认动态链接**，不需要
`BUILD_SHARED_LIBS=OFF` / `-static`（且上游该变量本就无分支，设了也无效）。
`/usr/lib/libcrypto.so.3` 虽存在，但 openssl 仅静态链入且 SONAME 不同，无冲突。

## 8. 上游测试清点与运行（R51 三步法）

### 8.1 清点（第一步）

| 清点项 | 命令 | 结果 |
|---|---|---|
| 测试源文件数 | `ls tests/*.c \| wc -l` | **11** |
| ctest 注册数 | 上游 CMakeLists `UNIT_TESTS` 列表（:304-341），`CHECK_FOUND` 时逐个 `jwt_add_test()` | **11**（与源文件一一对应） |
| 附加套件 | `tests/jwt-cli.bats`（bats 用例） | 9 例，**上游不注册**：`find_program(bats)` 探测不到即跳过（CMakeLists:297,342），镜像内无 bats |

11 个套件清单：`jwt_crypto`、`jwt_jwks`、`jwt_jwks_errors`、`jwt_ec`、`jwt_rsa`、`jwt_hs`、
`jwt_builder`、`jwt_checker`、`jwt_flipflop`、`jwt_claims`、`jwt_security`。

### 8.2 运行（第二步）

在 OHOS aarch64 真机上经 `conan create` 实际运行（不使用 ctest，理由见 §6-2），
结果见下方 §9 实测结果与 `test_package/MANIFEST.yml`。

**不可运行项的具体技术原因**（非"没环境"）：

- `jwt-cli.bats`（9 例）：镜像未提供 **bats** 测试框架（上游用 `find_program(bats)` 探测，
  探测不到即**上游自身**不注册该测试）。这不是配方裁剪——即使安装 bats，上游
  `add_test(NAME jwt_cli COMMAND /bin/bash -c ...)` 仍会因 OHOS 无 `/bin/bash` 而无法驱动，
  属上游硬编码解释器问题；该测试的端到端行为已由本配方 test_package（真实调用 CLI 与 API）
  部分覆盖。

### 8.3 回填（第三步）

实测 N/N′/通过率见 §9 与 PR 统计表（N=上游总数 11，N′=实际运行数 11）。

## 9. 实测结果

> 本机 OHOS aarch64 真机实测（2026-09-25），数据取自 `conan create` 全量重建日志
> （`--build="libjwt3/*"`，含上游测试与 test_package 两个阶段）。

### 9.1 上游测试（R51 第二步：实际运行）

**通过率 11/11 套件、147/147 checks、0 失败 0 错误（100%）**

| 套件 | rc | checks | failures | errors | 结果 |
|---|---|---|---|---|---|
| jwt_crypto | 0 | 1 | 0 | 0 | PASS |
| jwt_jwks | 0 | 5 | 0 | 0 | PASS |
| jwt_jwks_errors | 0 | 4 | 0 | 0 | PASS |
| jwt_ec | 0 | 4 | 0 | 0 | PASS |
| jwt_rsa | 0 | 8 | 0 | 0 | PASS |
| jwt_hs | 0 | 4 | 0 | 0 | PASS |
| jwt_builder | 0 | 18 | 0 | 0 | PASS |
| jwt_checker | 0 | 30 | 0 | 0 | PASS |
| jwt_flipflop | 0 | 22 | 0 | 0 | PASS |
| jwt_claims | 0 | 5 | 0 | 0 | PASS |
| jwt_security | 0 | 46 | 0 | 0 | PASS |
| **合计** | — | **147** | **0** | **0** | **11/11 PASS** |

### 9.2 test_package（消费者视角）

**通过率 50/50（100%）**，无 warning：

| 测试 | 项数 | 失败 | 说明 |
|---|---|---|---|
| `test_libjwt3` | 34 | 0 | JWKS 载入/取 JWK/HS256 签发/校验通过 + 篡改签名、篡改 payload、换密钥、非法令牌、claim 策略不符、exp 过期等负样本成对验证 |
| `test_ohos` | 16 | 0 | SONAME 加载、DT_SONAME/DT_NEEDED、v3 API 符号与 v2 移除、4 个 CLI 经 bindirs 可达（合法 ELF64）、/bin/sh 可执行 |

### 9.3 conan create

- 退出码：**0**（EXIT=0）
- package_id：`a87045f68ba2575c2c64510330eaf74cc5aa4077`
- 构建方式：`make -j1` 串行，2 个可执行目标 + 库目标全部 Built
- 编译告警：**0**（`warning:` 计数为 0）

### 9.4 「任务原计划 vs 实际做法」的偏差（如实记录）

1. **codegen 补丁的修法在实测中升级**：首版补丁只做「去掉 `bash -c` 包装」，首轮
   `conan create` 失败于
   `clang-15: error: unknown argument: '-fPIC -O2'`。根因是 `${CMAKE_C_FLAGS}` 的值
   （`-fPIC -O2`）作为**单个参数**传入编译器。最终修法改为用
   `separate_arguments(JWT_CODEGEN_FLAGS NATIVE_COMMAND "${CMAKE_C_FLAGS}")` 正确拆词，
   再以 `${JWT_CODEGEN_FLAGS}` 展开（保持 CMake 语义、不引入平台宏）。
   > 同源包 `libjwt/3.3.3` 采用的替代方案是在 conanfile 里 `subprocess` 预生成两个 `.i`
   > 并在 `package()` 时清理；本包改为**在源码层修根因**，因此不需要预生成 hack。
2. **exp 负样本的实现方式修正**：`jwt_checker_claim_set()` 依上游文档只接受
   `JWT_CLAIM_ISS/AUD/SUB`（字符串 claim），对 `JWT_CLAIM_EXP` 返回非 0。exp/nbf 须用
   `jwt_checker_time_leeway()` 开启并设 leeway（等价上游 `tests/jwt_claims.c`），
   故该负样本改为「1 秒后过期 → sleep → 校验必须失败 → 放宽 leeway 后必须通过」的
   成对形式，既验证负样本又证明失败确由 exp 触发。
3. **本包与同源包的关系**：`libjwt/3.3.3` 已存在于 main（status: built）。本包按任务
   要求以 `name="libjwt3"` 独立交付，CMake 目标名定为 `libjwt3::jwt`（避免与上游自带
   `LibJWTConfig.cmake` 及同源 `libjwt` 的目标名冲突），`pkg_config_name` 保持 `libjwt`。


## 10. 产物与 commands.json（R38）

上游 `jwt_add_tool()` 无条件构建并 `install(TARGETS ... RUNTIME DESTINATION bin)` 4 个 CLI →
产物含可执行文件 → 按 R38 在**软件级**目录创建 `commands.json`
（`archives/l/libjwt3/commands.json`，`type: "tool"`，`versions.3.3.3.ref = "libjwt3/3.3.3"`）。

| 产物 | 路径 |
|---|---|
| 共享库 | `lib/libjwt.so` |
| 静态库 | `lib/libjwt.a` |
| 命令行工具 | `bin/jwt-verify`、`bin/jwt-generate`、`bin/jwk2key`、`bin/key2jwk` |
| 头文件 | `include/jwt.h`、`include/jwt_export.h` |

## 11. 与同源包的关系

| 包 | 版本 | 关系 |
|---|---|---|
| `libjwt3`（本包） | 3.3.3 | 本次新建；`name="libjwt3"`，CMake 目标 `libjwt3::jwt`，`pkg_config_name=libjwt` |
| `libjwt` | 3.3.3 | 同源同版本，独立包（`name="libjwt"`，目标 `libjwt::libjwt`） |
| `libjwt-tools` | 3.3.3 | 同源，仅交付 4 个 CLI（`package_type=application`） |
| `libjwt2` | 2.1.3 | 2.x 线，API 不兼容 |

> 说明：CMake 目标名用 `libjwt3::jwt` 而非上游的 `LibJWT::jwt`，避免与上游自带
> `LibJWTConfig.cmake` 及同源 `libjwt` 包的目标名在同一构建树中冲突；
> `pkg_config_name` 保持 `libjwt`（与上游 `libjwt.pc` 一致，供 pkg-config 消费者使用）。
---

**编译结束**: 2026-09-26 00:57
**最终状态**: built
