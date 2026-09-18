# libjwt-tools 3.3.3 适配笔记

## 概述

- **软件**：libjwt-tools（libJWT 命令行工具集，取自 libjwt 源码树 `tools/` 子目录）
- **版本**：3.3.3（上游 tag `v3.3.3`）
- **官方源**：https://github.com/benmcollins/libjwt/archive/refs/tags/v3.3.3.tar.gz
- **sha256**：`a562e5548a8e10ac6fcba64a5e6d326c15712211cb54d25242c15e8b3250b4f2`
  （与同源父包 `libjwt/3.3.3` 同一归档、同一校验值，本机实测下载校验一致）
- **许可证**：MPL-2.0
- **构建系统**：CMake
- **包类型**：`application` —— 只交付 4 个可执行文件 + 4 个 man page，不含头文件与库
- **拆包关系**：同源子包（`libjwt-tools` requires `libjwt/3.3.3`，同版本）
- **补丁**：1 个（沿用父包 `patches/0001-cmake-fix-codegen-bash-c.patch`）

## 上游结构调查

`CMakeLists.txt` 中工具目标由 `jwt_add_tool()` 宏（上游未打补丁时第 179-205 行；
打上 `0001-cmake-fix-codegen-bash-c.patch` 后为第 177-203 行）声明，
位于 `if(WITH_TESTS)` 块（上游第 292 行 / 打补丁后第 290 行）**之外**，因此关闭 `WITH_TESTS` 不影响工具构建：

- 4 个工具：`jwt-verify`、`jwt-generate`、`jwk2key`、`key2jwk`
- 每个工具：`add_executable(<name> tools/<name>.c)` +
  `target_link_libraries(<name> PRIVATE jwt_static ${OPENSSL_LIBRARIES} ...)` +
  `install(TARGETS <name> RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})`
- 另有 `install(DIRECTORY tools/ ... PATTERN "*.1")` 安装 4 个 man page
- 依赖定位方式为 `pkg_check_modules()`（pkg-config），**不是** `find_package()`：
  - `pkg_check_modules(JANSSON jansson>=2.0 REQUIRED)`
  - `pkg_check_modules(OPENSSL openssl>=3.0.0 REQUIRED)`（CMakeLists.txt:71）

### 测试入口审计

- `add_test(NAME jwt_cli ...)` 运行 `tests/jwt-cli.bats`，**9 个 `@test` 用例**。
- 该 `add_test` 只在 `find_program(bats ...)` 命中时注册；本机镜像无 `bats`，
  上游优雅降级为不注册（属上游行为，非配方裁剪）。
- 因此本配方**逐条等价复现** 9 个 bats 用例），并把统计写入
  `HMBS_UPSTREAM_TEST_RESULT` 标记（详见下文「上游测试」）。
- `tools/` 目录自身不含单元测试；工具的功能语义全部由 `tests/jwt-cli.bats` 覆盖。

## W0 依赖核验

| 依赖 | 类型 | R35 核验 |
| --- | --- | --- |
| `libjwt/3.3.3` | 本体（requires） | `conan download -r=ohpcd --only-recipe` EXIT=0 |
| `openssl/3.5.6` | 直接依赖（requires，**必须显式声明**） | EXIT=0 |
| `jansson/2.15.1.1` | 经 libjwt 传递可见 | EXIT=0 |

对照组 `zzz-definitely-not-exist/9.9.9` EXIT=1，证明探测有效。
`check/0.15.2` 是 **父包** libjwt 的 `test_requires`，不向下游传播；
图谱实测中它是本包图里唯一的 `Skipped binaries`（符合预期）。

## 构建策略（继承父包 libjwt 的全部真机踩坑修复）

1. **PkgConfigDeps**：上游依赖定位走 `pkg_check_modules()`，`CMakeDeps` 不够，
   必须 `PkgConfigDeps(self).generate()` 产出 `.pc`。
2. **串行构建绕开 jobserver 竞态**：不使用 `cmake.build()`（会注入 `-jN`），
   改用 `subprocess` 直接跑 `make -j1 jwt-verify jwt-generate jwk2key key2jwk`，
   并把 SDK `llvm/lib` 前置进 `LD_LIBRARY_PATH`（lld 运行时需要 `libxml2.so.16`）。
   `-j1` 只编 4 个工具 + 1 个静态库，代价可忽略。
3. **预生成 codegen 文件**：上游 `add_custom_command(COMMAND bash -c "...")` 引号拆词
   （补丁 0001 已改为直接调 `${CMAKE_C_COMPILER} -E`）；配方另外预生成
   `jwt-builder.i` / `jwt-checker.i`，彻底跳过 make 的 codegen 步骤。
4. **HarmonyOS SONAME 补偿三行**：与父包一致 ——
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` +
   `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` / `CXX_FLAG` = `-Wl,-soname,`。
   （本包虽不交付共享库，但上游仍会构建 `jwt_static`/`jwt` 目标，缺这三行会在链接期暴露问题。）
5. **工具包不跑 ctest**：上游 `add_test()` 硬编码解释器 `/bin/bash`，OHOS 只有 `/bin/sh`。

## 两个真实失败的定位与修复

### 失败 1：`No package 'openssl' found`（构建期，必须修配方）

**首个错误**

```
-- Checking for module 'jansson>=2.0'
--   Found jansson, version 2.15.1.1
-- Checking for module 'openssl>=3.0.0'
--   No package 'openssl' found
CMake Error at .../FindPkgConfig.cmake:639 (message):
  The following required packages were not found:
   - openssl>=3.0.0
Call Stack: CMakeLists.txt:71 (pkg_check_modules)
ERROR: libjwt-tools/3.3.3: Error in build() method, line 126
```

**现象**：generators 目录里只有 `jansson.pc` 与 `libjwt.pc`，**没有 `openssl.pc`**。

**根因（conan 2.29.1，已用 `conan graph info` + 探针实证）**

`openssl` 不在 `self.dependencies.host` 里。链路：

1. `libjwt` 的 `package_info()` 只暴露 `cpp_info.libs = ["jwt"]`，openssl 的
   `libcrypto.a/libssl.a` 已静态链入 `libjwt.so`（`libjwt.so` 的 `DT_NEEDED` 只有
   `libjansson.so` + `libc.so`），因此在 libjwt 这一层 openssl 是 `run=false / libs=true`；
2. 该 require 经 `conan/internal/graph/graph.py:154`
   `Requirement.transform_downstream()` 传播到消费者（本包）时变成
   **`run=false / libs=false`**；
3. `conan/internal/graph/graph_binaries.py:556-564` 的 `_skip_binaries()`：
   对根节点只把 **direct** require 放进 `deps_required`，于是该边
   `require.skip = True`，节点 `binary` 变为 `BINARY_SKIP`；
4. `conan/internal/model/dependencies.py:166-167`
   ```python
   @property
   def host(self):
       return self.filter({"build": False, "test": False, "skip": False})
   ```
   → openssl 被过滤掉；
5. `conan/tools/gnu/pkgconfigdeps.py:335 & 364` 的 `_get_dependencies()` 正是遍历
   `dependencies.host` → **不产出 `openssl.pc`**；
6. 上游 `CMakeLists.txt:71` 的 `pkg_check_modules(OPENSSL ... REQUIRED)` 报错，构建中断。

`conan graph info` 实测（消费者 → 依赖）：

| 边 | direct | skip | run | libs | binary |
| --- | --- | --- | --- | --- | --- |
| → `libjwt/3.3.3` | true | false | true | true | Cache |
| → `jansson/2.15.1.1` | false | false | **true** | false | Cache |
| → `openssl/3.5.6` | false | **true** | **false** | false | **Skip** |

**jansson 为何不受影响**：`libjwt.so` 动态依赖 `libjansson.so`（`run=true`）→ `skip=false`。
**父包 libjwt 为何不受影响**：openssl 是父包自己的 direct require。

**修复**：在 `requirements()` 中把 `openssl/3.5.6` 声明为本包的 **direct require**。
消费者根节点的 direct require 一定进入 `deps_required`，`skip=false`，
`PkgConfigDeps` 随即产出带 `-L${libdir} -lssl -lcrypto -ldl -lpthread` 的 `openssl.pc`。

**重新验证**：`conan graph info` 变为 `openssl direct=true / skip=false`，
构建期 `-- Found OpenSSL`，`conan create` EXIT=0。

### 失败 2：test_package `fatal error: 'jwt.h' file not found`（测试期）

**首个错误**

```
test_package: [ 25%] Building C object CMakeFiles/test_consumer.dir/test_consumer.c.obj
test_package: test_consumer.c:15:10: fatal error: 'jwt.h' file not found
```

**根因**：`libjwt-tools` 的 `package_type = "application"`，只把 `bin/` 暴露给消费者，
不 re-export libjwt 的头/库。于是 libjwt 在 test_package 图里处于**传递**位置，
Conan 按 `headers=False / libs=False` 过滤其 `cpp_info`，CMakeDeps 生成的
`libjwt-release-armv8-data.cmake` 中：

```cmake
set(libjwt_PACKAGE_FOLDER_RELEASE ".../libjw782d459f8f4f6/p")
set(libjwt_INCLUDE_DIRS_RELEASE )                      # ← 空
set(libjwt_LIBS_RELEASE )                              # ← 空
set(libjwt_LIB_DIRS_RELEASE "${...}/lib")              # 正常
set(libjwt_BIN_DIRS_RELEASE "${...}/bin")              # 正常
set(libjwt_SYSTEM_LIBS_RELEASE m pthread)              # 正常
```

即 `LIB_DIRS/BIN_DIRS/SYSTEM_LIBS` 正常、仅 `INCLUDE_DIRS/LIBS` 为空 → 排除
「包内缺文件」与「cpp_info 写错」，确认是**传递过滤**（包内 `include/jwt.h`、
`lib/libjwt.so`、`lib/libjwt.a` 均在）。

**修复**：`test_package/conanfile.py` 的 `requirements()` 中额外
`self.requires("libjwt/3.3.3")`，使 libjwt 成为 test_package 的直接依赖，
`libjwt::libjwt` 的 `INTERFACE_INCLUDE_DIRECTORIES` 与 `-ljwt` 正常导出。

**重新验证**：`test_consumer` 编译链接通过，运行 12/12 断言全通过。

## 上游测试

- **框架**：bats（`tests/jwt-cli.bats`）
- **上游注册方式**：`add_test(NAME jwt_cli ...)`，仅在 `find_program(bats)` 命中时注册
- **执行命令**：逐条复现 9 个 `@test`（镜像无 bats），在 build 目录内执行 `./tools/<tool>`
- **统计**：discovered 9 / executed 9 / **passed 9** / failed 0 / skipped 0

| # | 用例名 | 结果 |
| --- | --- | --- |
| 1 | Generate a JWT with alg none | PASS |
| 2 | Verify a JWT with alg none | PASS |
| 3 | Generate a JWT with alg HS256 | PASS |
| 4 | Verify a JWT with alg HS256 | PASS |
| 5 | Generate a JWT with alg HS256 and claims | PASS |
| 6 | Verify a JWT with alg HS256 with claims | PASS |
| 7 | Generate JWKS from PEM Files | PASS |
| 8 | Convert JWK to PEM - RSA | PASS |
| 9 | Convert JWK to PEM - OCT | PASS |

**已知偏差（如实登记，未裁剪任何用例）**

1. 用例 3-6 的密钥路径：上游 bats 写 `../tests/keys/oct_key_256.json`（假定 build 目录
   位于源码树内），本配方用源码树绝对路径等价替代。
2. 用例 7 的 JSON 等价比较：上游用 `jq`（`normalize = walk(if type == "array" then sort else . end)`），
   OHOS 镜像无 `jq`，本配方用 `python3` 复现同一 `normalize`/`equiv` 语义
   （实测 23,864 字节输出与 `tests/cli/all.json` 语义等价）。
3. 镜像无 `bats`，故不通过 ctest 驱动；用例语义逐条对齐，未跳过任何用例。

## test_package（消费者用例）

- `test_consumer`（C，12 断言）：JWKS 装载 → `jwt_builder_new/setkey/generate` →
  `jwt_checker_new/setkey/verify` → 篡改 token 负样本。
- **`test_ohos`（C，21 断言）—— 本适配新增的鸿蒙消费者用例**：对 4 个工具逐一断言
  ①经 Conan `bindirs` 通道可达（`access(X_OK)`）、②ELF64 且 `e_machine == 183`（AArch64）、
  ③含 `PT_INTERP`、④`DT_NEEDED` 含 `libjansson.so`、⑤`DT_NEEDED` **不含** `libjwt.so`
  （证明上游 `jwt_add_tool()` 用 `PRIVATE jwt_static` 静态链接本体，工具交付物
  不依赖本体共享库），并断言 `/bin/sh` 可执行。
  该用例在 C 层刻意不做 `fork/exec`（OHOS 对跨二进制 spawn 有额外管控，见
  `archives/l/libjwt/3.3.3/notes.md` 同款处理），工具的动态功能验证放在 Python 层的端到端。
- 工具端到端（Python，4 断言）：`key2jwk` 生成 JWK → `jwt-generate` 签发三段式 token
  → `jwt-verify` 校验通过（rc=0）→ 篡改 token 被拒绝（rc=1）。
- **合计 37/37 通过**（`HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 37, "passedCount": 37}`）。

## 交付物

```
bin/jwt-verify      bin/jwt-generate      bin/jwk2key      bin/key2jwk
share/man/man1/jwt-verify.1  jwt-generate.1  jwk2key.1  key2jwk.1
licenses/LICENSE
```

4 个可执行文件均为 ELF64 AArch64（`e_machine=183`）且带 `PT_INTERP`，
`DT_NEEDED` 仅 `libjansson.so` + `libc.so`。

## 日志取证说明（一次日志串写残留物的定位）

在整理证据日志时发现 `reports/testlogs/test_ohos.log` 的内容与同一次运行的结论标记不一致：
该文件有 16 条 `FAIL:`，而 `HMBS_TEST_PACKAGE_RESULT` 标记为 `test_ohos ok=21 fail=0`。
按「以原始日志为准」的原则，本适配没有把它当作已通过，而是先定位、再复跑取证。

**判定该文件不是任何一次成功运行的原始日志，依据有三条：**

1. **行序在单次顺序执行下不可能出现。** `test_ohos.c` 的 `main()` 按「工具① 5 项 →
   工具② 5 项 → …」顺序输出，每组 5 项必然连续。该文件里 4 条
   `ok: DT_NEEDED 不含 libjwt.so` 被**全部挤到文件末尾**（第 19-22 行），
   而它们的正确位置应是第 5/10/15/20 行，中间还插着 `16 check(s) FAILED` 汇总行
   （汇总行理应在文件最后）。即该文件是多条写路径交错写入的结果，不是单次运行产物。
2. **其 bindir 不属于任何一次成功运行。** 文件首行记录
   `LIBJWT_TOOLS_BINDIR=…/p/b/libjw8ad1de6fb036a/p/bin`，而三次成功运行分别是
   `libjwdd90ef7df7423` / `libjw4c853ba9c8b16` / `libjwb7d5e13acf1e3`。
3. **标记的计数逻辑决定了「失败日志」不可能与「exit 0」共存。**
   `test_package/conanfile.py:160` 用 `>"<out_path>"`（截断重定向）写日志，
   `:162-171` 再**读同一个文件**统计 `ok`/`FAIL` 行数，`:298-299` 以 `failed == 0`
   作为 `passed` 的条件，`:315-317` 不通过即抛 `ConanException`。
   所以若该文件真为某次运行的日志，那次运行必然以异常退出、不会报 `fail=0`。

**处理**：保留原件为 `reports/testlogs/test_ohos.stale-fail.log`（不动、不删，供复核），
并做一次从零开始（先 `rm -rf test_package/build`）的干净复跑取得权威日志。

**干净复跑结果（`reports/conan-create-final.log`）**

- 命令：`conan create . -pr:h=<abs>/ci/conan/profiles/ohos-aarch64 -pr:b=<同前> --build="libjwt-tools/*"`
- 退出码 **0**；`test_ohos ok=21 fail=0`、`test_consumer ok=12 fail=0`、上游 9/9 PASS
- 日志：`reports/conan-create-final.log`、`reports/testlogs/test_ohos.log`（21 `ok:` / 0 `FAIL:`，
  末行 `test libjwt-tools 3.3.3 ohos-specific: all checks passed`）
- 该次与上一次独立复跑（`reports/conan-create-rerun.log`）逐行对比，差异**仅**为
  时间戳、临时 build 目录哈希与耗秒数；`package_id = d5638da3e804c734402caf87ffefdafa9e205fd9`
  **多次完全一致**，即配方在内容维度确定可复现。
- 提交前审计后的两处收尾修正（均为**非功能性**改动）：
  1. `conanfile.py` 注释中的上游行号引用 `181-205` → `179-205`（对齐 pristine 真实行号）；
  2. `conanfile.py` 方法顺序 `export_sources → layout → requirements` 调整为
     `export_sources → requirements → layout`，对齐 `.gitcode/code-style.md` §3。
  两次改动后 `recipe revision` 依次变为 `034afc75…` → `b49cd66f9054e21e1c2c2888d64c12fb`，
  而 **`package_id` 始终保持 `d5638da3e804c734402caf87ffefdafa9e205fd9` 不变** ——
  这从二进制维度独立证明两次改动都未触及任何构建逻辑。
- **W3 的 L0i「依赖未发布」是一次环境假阳性（已定位并复验）**：`ci/conan/build_and_test.sh`
  用**裸名 `conan`** 探测依赖，而 `ci/conan/setup.sh` 导出的 `PATH`（含 `$HOME/.local/bin`）
  不会传播到作为独立进程启动的 `build_and_test.sh`；`conan` 因此解析失败（127），
  被 L0i 归类成 `dependency NOT in registry`。同轮实测对照：
  `bash ci/scripts/preflight_check.sh libjwt-tools/3.3.3` 在无 `conan` 的 PATH 下报
  「未发布: libjwt/3.3.3 / openssl/3.5.6」，把 `$HOME/.local/bin` 加回 PATH 后同一命令报
  「已发布: libjwt/3.3.3 / 已发布: openssl/3.5.6」。补上 PATH 后重跑 W3 即全绿
  （`L0_RESULT=pass`、`Pass rate: 100.0% (1/1)`）。**两个依赖一直是已发布状态。**

综上：`test_ohos` 21/21 通过为实测结论；那份红色文件是整理阶段的跨运行串写残留物，
不影响配方、包内容与本次验证结论。

## 参考

- 同源父包：`archives/l/libjwt/3.3.3/notes.md`
- 本地证据日志（均被 `.gitignore:96 reports/` 忽略，不入库）：
  - `reports/conan-create-final.log`（最终干净复跑，权威）
  - `reports/conan-create-rerun.log`（上一条独立复跑，用于可复现性对照）
  - `reports/conan-create.log`（首次完整通过）
  - `reports/w3-local-ci.log`、`reports/conan-verify-report.md`、`reports/finish-console.log`
  - `reports/testlogs/test_ohos.log`、`reports/testlogs/test_consumer.log`
  - `reports/testlogs/test_ohos.stale-fail.log`（见上「日志取证说明」，留档备查）
- `commands.json`（软件级，R38/L0k）：`archives/l/libjwt-tools/commands.json`
---

**编译结束**: 2026-09-18 11:43
**最终状态**: built
