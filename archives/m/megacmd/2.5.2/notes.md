# megacmd 2.5.2 适配笔记（含构建段实录 · 定稿）

> 取证段：主理-11（子代理·非构建前置取证段，禁构建、只读取证，即 §1–§4、§7）。
> 构建段：主理-22 / 主理-34（OHOS PC 真机，§5、§6、§8）。
> **本文件现含构建段实录**：`conan create`、`conan-verify`、`ctest` 真实执行与 W3 本地 CI 模拟均已完成，
> 最新一轮 W3（W4 整改后重跑）于 **2026-09-25 02:29:39** `exit_code=0` 全绿（凭据 `reports/w3-local-ci.log`，行号见 §8.5）。

## 0. 路径 B 最小声明（3+2，`prepr-body-gate` 要求；与 PR 正文同源）

- **适配路径**：路径 A+B（B 判定 = `create`，PR 标题前缀 `【知识库扩展】`）
- **使用知识库**：`hit(E150 manual-download)` —— tag 归档 `sdk/` 为空目录，按 E150 单独取 meganz/sdk pin commit 归档 tarball 并 sha256 校验后拷入（详见 §1、§7）
- **知识库扩展**：`create` —— 草稿 `knowledge/drafts/DRAFT-megacmd-2.5.2-upstream-vcpkg-bootstrap-takeover-system-deps.{kv,md}`（已过 draft-review，verdict=create）；机制：上游 CMake 默认在线 `git clone` vcpkg 并以其 toolchain 接管全部依赖（空 `VCPKG_ROOT` 挡不住，离线 configure FATAL）⇒ 补丁短路 clone 条件 + 跳过 vcpkg 产物安装块，强制走 system-deps 分支由 Conan 注入依赖
- **关联 Issue**：#3327


## 1. 源码取证

| 项 | 值 |
|---|---|
| 主仓 URL（官方 tag 归档） | `https://github.com/meganz/MEGAcmd/archive/refs/tags/2.5.2_Linux.tar.gz` |
| HTTP/大小/sha256/类型 | 200 / 2,123,577 B / `a088c001e9116357fcac92cd0b3d62fb53cc24ce546eb0fb4cc83c53df5eed7c` / gzip |
| tag 解析 | annotated tag `2.5.2_Linux`（object db3a7ea0…）→ commit `f40c31c81d90289ef0156fd67b0ff6f38c148a2d`（tagger Pablo Martin 2026-04-14） |
| tar 顶层 | CMakeLists.txt / .gitmodules / build / contrib / sdk / src / tests / vcpkg.json …（446 条目） |
| `.gitmodules` 原文 | 仅一段：`[submodule "sdk"] path = sdk / url = https://github.com/meganz/sdk.git` |
| 子模块 pin | `sdk` → `fae76a36d60484657fbdf442b7b917ccc4fbad77`（GitHub contents API @ f40c31c8 复核，type=submodule） |
| 子模块源 URL/sha256 | `https://codeload.github.com/meganz/sdk/tar.gz/fae76a36d60484657fbdf442b7b917ccc4fbad77` / `3df9f194e2f18b64d51b325c50f852e694d232380bfc83e03f96bf6281db91eb`（HTTP 200 / 4,528,326 B / gzip） |
| 嵌套子模块 | 无：sdk 官方 git tree @fae76a36 递归 2413 条目，mode=160000 零条、全树无 .gitmodules |
| tarball 中 `sdk/` | **空目录**（E150 症状实锤） |

E150 取源处方落地：`conanfile.source()` 主 tarball `strip_root` 后，再 `get()`
子模块 commit 归档到 `destination="sdk"`。**双通道字节级实证**：主仓 tag URL
实测 302→codeload（哈希 a088c001e9116357fcac92cd0b3d62fb53cc24ce546eb0fb4cc83c53df5eed7c）；sdk 的 `github.com/archive/<commit>.tar.gz`
与 `codeload…/tar.gz/<commit>` 各完整下载一次，两份 sha256 同为 3df9f194e2f18b64d51b325c50f852e694d232380bfc83e03f96bf6281db91eb，
逐字节一致（证据 `sdk-url-sha256-verified.txt`）。sdk 一层取源即完整（无孙模块）。

## 2. 构建系统结论

- **构建系统**：CMake 单构建系统（顶层仅 1 个 CMakeLists + build/cmake/modules 模块）；另有 vcpkg.json manifest（vcpkg 是默认依赖通道，本配方绕开）。
- **cmake 版本**：顶层 `cmake_minimum_required(3.16)`；sdk 子项目 `3.20` ⇒ **实际门槛 3.20**（本机 cmake 4.1.2）。
- **C++ 标准**：**17**（`build/cmake/modules/megacmd_configuration.cmake` 与 sdk `cmake/modules/configuration.cmake` 双处 `CMAKE_CXX_STANDARD 17` + REQUIRED）。
- **find_package / pkg 面**（system-deps 分支，`VCPKG_ROOT` 空时）：
  - 顶层：`find_package(Git REQUIRED)`（取 SDK_COMMIT_HASH，无 .git 时仅输出空、非致命）；`find_package(PkgConfig REQUIRED)` + `pkg_check_modules(libpcre)`。
  - sdk `sdklib_libraries.cmake`：vcpkg 分支 `cryptopp/unofficial-sodium/unofficial-sqlite3/CURL/OpenSSL/ZenLib|MediaInfoLib/freeimage/FFMPEG/libuv/pdfium/ICU/Readline-unix/Curses`；**system 分支** `pkg: libcrypto++、libsodium、sqlite3、libcurl、openssl、libmediainfo、libavformat 等五件套、libuv、pdfium、readline` + `find_package(ICU / OpenSSL / FreeImage)`；FUSE 走自带 `FindFUSE.cmake`（找 `include/fuse3` + `libfuse3.so`）。
  - ZLIB：**两棵树都没有直接 find_package(ZLIB)**，经 libcurl 传递（台账声明的 ZLIB 由此解释）。
- **FetchContent/ExternalProject/CPM**：**两棵源树零命中**（grep 全量）。真正的在线雷是 **vcpkg 在线克隆**：顶层 CMakeLists 42-56 行在 `VCPKG_ROOT`（默认 `../vcpkg`）不存在时 `bash build/clone_vcpkg_from_baseline.sh` → `curl api.github.com` 取日期 + `git clone --shallow-since … https://github.com/microsoft/vcpkg`。README 原话：“All dependencies are downloaded and installed automatically by vcpkg”。
- **绕法（已做成补丁并 dry-run 验证 RC=0）**：`patches/0001-skip-vcpkg-online-clone.patch`
  1. clone 条件前置 `VCPKG_ROOT AND …` ⇒ 配方传 `-DVCPKG_ROOT=` 时跳过在线 clone；
  2. 跳过 `install(DIRECTORY ${vcpkg_lib_folder})` 块（**隐患**：VCPKG_INSTALLED_DIR 为空时路径退化为 `/lib/`，会把宿主系统 .so 打进包）；
  3. `if(VCPKG_ROOT)` 走上游自带 `else` ⇒ “Using system dependencies” 分支。
  - `cmake -P` 语言级探测（不编译）证实：空 `VCPKG_ROOT` ⇒ clone 条件仍为真（**必须**补丁）+ system-deps 分支为真；指向已存在目录 ⇒ 不 clone 但进 vcpkg 管理分支并在缺 `vcpkg.cmake` 时 FATAL（死路）。证据 `vcpkg-branch-probe.txt`。
- **MEGA SDK 集成方式**：不是 find_package，而是 **git submodule 源码内嵌**：顶层 `add_subdirectory(sdk)`，目标 `MEGA::SDKlib` 链进 4 个可执行与 2 个静态库；sdk 作为子项目时其自身 vcpkg 块不执行（`if(NOT PROJECT_NAME)` 为假），tests/examples/werror 默认关。
- **开关清单**（确切名）：
  - **fuse3 关闭 = `-DWITH_FUSE=OFF`**（64 位 Linux `option(WITH_FUSE … ON)` 默认开；sdk `src/fuse/CMakeLists.txt` 关闭时走 dummy backend `unsupported/`，且 megacmd 源码宏 `WITH_FUSE` 不定义、`megacmd_fuse.cpp` 主体 41-441 行整块 `#ifdef WITH_FUSE` 排除；上游 SynologyNAS 交叉构建 Dockerfile 同款用法 `-DWITH_FUSE=OFF`）。
  - `-DFULL_REQS=OFF`（否则 `REQUIRE_HAVE_FFMPEG/REQUIRE_HAVE_PDFIUM/REQUIRE_USE_MEDIAINFO/REQUIRE_HAVE_LIBUV/REQUIRE_USE_PCRE` 强制五件套）。
  - `-DUSE_FFMPEG=OFF / -DUSE_PDFIUM=OFF / -DUSE_FREEIMAGE=OFF / -DUSE_MEDIAINFO=OFF`（裁剪）；`USE_MEDIAINFO=ON 而 ENABLE_MEDIA_FILE_METADATA=OFF 会 FATAL`（sdk 自检）。
  - `-DENABLE_MEGACMD_TESTS=OFF`（Release 默认即 OFF；且 system-deps 分支开 ON 会因 `GTest::gtest` 未定义而 configure 失败——`find_package(GTest)` 仅在 VCPKG 分支）。
  - 其他：`USE_LIBUV`（megacmd 强制 ON）、`USE_READLINE`（默认 ON）、`USE_PCRE`（默认 ON）、`ENABLE_SDKLIB_{TESTS,EXAMPLES,WERROR}`、`ENABLE_ASAN/UBSAN/TSAN`、`ENABLE_C_ARES_BACKEND`。

## 3. W0 依赖核验（只读，`conan download <ref> -r ohpcd --only-recipe`，证据 `w0-conan-recipe-checks.txt`）

**全部 RC=0（recipe 已发布）**：zlib/1.3.1、pcre/8.45、sqlite3/3.53.4、openssl/3.5.6、libcurl/8.5.0、cryptopp/8.9.0、libuv/1.52.1、libsodium/1.0.22、icu/76.1、readline/8.3、ffmpeg/7.1.5、freeimage/3.18.0、libmediainfo/25.07、pdfium/152.0.7947.0、gtest/1.17.0。

**配方缺口（未发布，非本窗 block）**：
- `fuse3`：`conan list fuse3/* -r=ohpcd` → 0 条（**无该命名 recipe**；`libfuse/3.18.2`、`libfuse/2.9.9` 存在）。因默认 `WITH_FUSE=OFF` 不进 requires ⇒ 当前不构成阻塞。
- `zenlib`：`conan list zenlib/* -r=ohpcd` → 0 条。libmediainfo 的传递依赖；**仅在打开 USE_MEDIAINFO 时才成为缺口**，本配方默认关。

**二进制层不作结论**（本窗只跑 `--only-recipe`；本地 install RC=0 也只算 Cache 命中）。

## 4. 语言面自证（lang-preflight 属构建段，未跑；本窗只读统计，见 `language-stats.txt`）

- MEGAcmd 本体：45 个 .cpp、30 个 .h、2 个 .mm，C/C++ 合计 47,871 行；其余为 md(85)/bat(67)/sh(15)/py(8) 等文档与脚本。
- sdk 子模块：几乎全部为 C++ 源（树内唯一显著非代码为文档/打包文件）。
- 结论：**主语言 cpp，与任务声明一致**；构建系统 cmake 单一，与台账一致；无语言迁移、无 env_unsupported 嫌疑。

## 5. 上游测试清点与实测（R51 证据；构建段已真实执行）

- `tests/`：18 个 .cpp（unit 6+main、integration 9+main、common 2）+ **12 个 shell/python 脚本文件**（5 个 `.sh` + 7 个 `.py`；其中 `megacmd_tests_common.py` 为无用例的公共辅助模块 ⇒ **可执行脚本用例计 11**，与下方五维口径的 157 同口径）。
- **CTest 零注册**：两棵树 `enable_testing/add_test/ctest` 零命中——测试只以可执行文件形式存在，需手动运行。
- 构建开关 `ENABLE_MEGACMD_TESTS`（Debug 默认 ON，Release 默认 OFF）；**system-deps 分支下开 ON 原会 configure 失败**（`GTest::gtest` 只在 vcpkg 分支 `find_package(GTest CONFIG)`）⇒ 补丁 `0004-gtest-unit-tests.patch` 在无 vcpkg 分支补上 `find_package(GTest CONFIG REQUIRED)`，并把 8 个单元套件逐套件注册进 ctest；配方据此置 `ENABLE_MEGACMD_TESTS=ON`，`build()` 内 `ctest -V` 真实执行 + 文档化基线断言。
- **实测（conan create 内）**：`upstream tests/unit baseline: SUITES_STATIC=8 SUITES_EXECUTED=8 TOTAL=70 PASS=47 FAIL=23`；23 例失败与 2 例未执行全部为平台能力限制（AF_UNIX 路径套接字 / 只读 /tmp / chmod 位），逐条申报见 `reports/test-report.md` §4。集成测试 59 例与 11 个脚本需真实 MEGA 账号 + 公网，未执行（二进制已成功编译链接）。
- **五维口径（与最新一轮日志锁定，勿混用）**：静态注册 **72** = 各套件 `Running N tests` 之和；ctest 启动 **71**；产出结论 **70**（= `TOTAL=70`，PASS 47 + FAIL 23）；未出结论 **2**（1 例随套件段错误中断、1 例从未启动）；套件级判决 8 条 → 4 Passed / 4 Failed（其中 3 条 `***Failed` + 1 条 `***Exception: SegFault`，汇总行 `50% tests passed, 4 tests failed out of 8`）。上游静态声明总量 **157**（单元 87 宏 + 集成 59 + 脚本 11）属源码宏清点，**不由日志复核**。

## 6. 构建段验证清单（W3 逐项销账，全部已实测）

1. ✅ 补丁 0001 生效：configure 完全脱离 vcpkg（日志出现 “Using system dependencies”，无 “vcpkg will be cloned”；`-DVCPKG_ROOT=` 必须走**命令行 cache 条目**——上游第 29 行在 `project()` 之前 `set(... CACHE PATH)` 钉死默认值，`tc.variables` 抢不到）。
2. ✅ 依赖注入：system-deps 分支原只用 pkg-config，而 Conan 只产 CMake config（cryptopp 上游无 `.pc`）⇒ 补丁 `0002` 改为 config 优先 + pkg-config 回退，并把 8 处依赖的链接可见性由 PRIVATE 改 PUBLIC（上游公共头 `<curl/curl.h>`/`<pcrecpp.h>` 泄漏到 LMegacmdServer 编译单元）。全部选项经 `tc.cache_variables`（conan 展开为命令行 `-D`）下发——上游 `project()` 之前就 `include(megacmd_options)`/`include(sdklib_options)`，`tc.variables` 会被 `option()` 抢占。
3. ✅ 安装布局：`usr/bin → bin` 归一化；`opt/megacmd/lib` 为空（依赖全静态/共享由 Conan 提供）。⚠ 上游 install 会**改写 ELF RUNPATH** 为 `<prefix>/opt/megacmd/lib`，该改写使链接期 ELF 签名失效 ⇒ 设备执行报 EPERM，配方 `package()` 已重新自签名（见 §8.3）。
4. ✅ test_package 冒烟：`mega-cmd --version` 无需常驻 server 即可执行并出 banner（`timeout` 兜底已有）。**但功能级命令都需要 server**，而 server 受 §8.4 两项平台限制阻塞 ⇒ 消费者测试按"二进制可加载可运行"判定，如实申报不伪造。
5. ✅ `full_reqs`/`with_fuse` 保持 OFF（fuse3/zenlib 缺口由此绕开，未 block）。
6. ✅ 依赖求解：`zlib` 必须钉 `1.3.1.1`（`libcurl/8.5.0` 精确钉该版本，写 `1.3.1` 会报 Conflict）；`gtest/1.17.0` 走 `test_requires`。

## 7. B 判定建议（判定权在主理）

- **`B判定=create`（主推）**：机制一句话 —— 「上游 CMake 默认在线 git clone vcpkg 并以其 toolchain 接管全部依赖（OHOS/离线 CI 断网即 configure FATAL）⇒ 补丁短路 clone 条件 + 跳过 vcpkg 产物安装块（防空 VCPKG_INSTALLED_DIR 把 /lib 打进包），强制走 system-deps 分支由 Conan 注入依赖」。知识库 `knowledge/doc/` 与 `graph/index.tsv` 对 `vcpkg` **零命中**；E342 只覆盖测试框架的 configure 期下载（机制不同：toolchain 级 bootstrap），组合型知识不判重。可把 fuse3/WITH_FUSE=OFF 关闭作为同条机制的组成段。
- **submodule 取源部分 = `hit(E150 manual-download)`（写进「使用知识库」行）**：①症状一致（tag 归档含 .gitmodules、`sdk/` 空目录，add_subdirectory(sdk) 必炸；E150 错误特征含 `submodule.*missing`/`fatal: not a git repository`，顶层恰有 `git rev-parse` on sdk）；②解法已被 E150 覆盖（单独取子模块源拷入）；③引用精确（E150 + manual-download 命令形态）；④等效性（本窗用 codeload commit tarball 替代 `git clone --depth=1 + checkout <commit>`：同一 commit tree、官方托管、sha256 可校验、离线可复现——等效且更强，已在本文件 §1 留证）。
- E425（pico-sdk 空子模块保持占位）不适用：MEGAcmd **必须**要 sdk 内容（add_subdirectory(sdk) 是构建本体），不能留空占位。

## 8. 构建段实录（主理-22，2026-09-24，OHOS PC 真机）

### 8.1 四个补丁（全部对上游原文 dry-run / 真机复现验证）

| 补丁 | 作用 |
|---|---|
| `0001-skip-vcpkg-online-clone.patch` | 短路顶层在线 vcpkg clone（`VCPKG_ROOT AND …`）+ 跳过 vcpkg 产物安装块（防 `VCPKG_INSTALLED_DIR` 为空时把宿主 `/lib` 打进包） |
| `0002-system-deps-via-cmake-config.patch` | system-deps 分支改走 CMake config 包（pkg-config 回退）+ 8 处依赖 PRIVATE→PUBLIC（公共头泄漏） |
| `0003-clang-libcxx-portability.patch` | `<algorithm>`（`std::min`）、`<fcntl.h>`（`O_RDWR/O_CREAT/F_SETFD/FD_CLOEXEC`）、`stdc++fs` 仅非 Clang 链接 |
| `0004-gtest-unit-tests.patch` | 无 vcpkg 分支接 `find_package(GTest CONFIG)`；顶层 `enable_testing()` + 8 个单元套件逐套件 `add_test` |

### 8.2 三个必须在构建段才暴露的坑（均已修）

1. **`CMAKE_SYSTEM_NAME` 必须是 `Linux`**：OHOS profile 的 triplet 令 CMake 把系统名推成 `HarmonyOS`，CMake 无该 platform module ⇒ `UNIX` 为假 ⇒ 上游 `#ifdef UNIX` 的公共头包含链断裂（`megagfx.h:32 'megawaiter.h' file not found`，14 处）。配方按仓库既有先例（E092，407 处）置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`。
2. **`apply_conandata_patches` 只能调一次**：`source()` 与 `build()` 同时调用时，因 conan create 会把 `source_folder` 整体拷进 build folder，二次打补丁必报 `source file is different`。该 bug 平时被 conan 的 source 缓存掩盖（`source()` 不重跑时只剩 `build()` 生效），一旦改 `conanfile.py` 使 recipe revision 变化、`source()` 重跑就立刻暴露。**补丁只打一次，固定在 `source()`**。
3. **GTest 目标名**：Conan 的 `gtest/1.17.0` 只声明 `gtest::gtest`（无 gmock），但同一包里装了上游 `GTestConfig.cmake`（含 `GTest::gtest`/`GTest::gmock`）⇒ 配方显式钉 `GTest_DIR=<pkg>/lib/cmake/GTest`，补丁里即可用与 vcpkg 分支一致的目标名。

### 8.3 包内运行时归一化（`package()`，仅 OHOS）

- **ELF 重新自签名**：`cmake install` 改写 RUNPATH ⇒ 链接期签名失效 ⇒ 设备执行包内二进制报 `Operation not permitted`（同一构建的 build 目录副本可执行，install 副本 RC=126）。按 libcurl 配方同款：`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`（路径可用 `HNP_OBJCOPY`/`HNP_SIGN_TOOL` 覆盖）。**实测（最新一轮）：包内 `mega-cmd` 在 Conan runenv 下执行成功并产出 MEGAcmd banner**（判定者是 `test_package`，其 `test()` 以 `env="conanrun"` 执行 ⇒ 带 `PATH` 与 `LD_LIBRARY_PATH`；证据 `w3-local-ci.log:5692-5699`，签名动作 `5604-5635`）。**注意边界**：W3 的 L2 冒烟步对同一批文件全部判失败（`L2_RESULT=skip`），已定性为**判据环境缺陷**而非本包回归，详见 §8.5。
- **包装脚本 shebang**：上游 68 个 `mega-*` 包装脚本写死 `#!/bin/bash`，而 OHOS PC 无 `/bin/bash`（实测 `/bin/sh` 是 mksh，bash 在 `/data/service/hnp/bin` 或 `~/.harmonybrew/bin`）⇒ 全部以 `No such file or directory` 失败。改为 `#!/usr/bin/env bash`（与仓库自身 `ci/scripts/preflight_check.sh` 一致）。
  - **已证事实（最新一轮）**：包内 68 个包装脚本的 shebang 确已归一化——`w3-local-ci.log:5604` 打印该动作，且包目录内 `bin/mega-ls` 文件头实测为 `#!/usr/bin/env bash`（正文体为 `mega-exec ls "$@"`，即以**裸命令名**调用 ⇒ 必须有 `PATH` 指向包 `bin/`，该 `PATH` 由 `conanrun` 注入）。
  - **如实降级（不得保留的强结论）**：早前写的「实测：修复后 `mega-ls` 可执行」**在最新一轮没有证据支撑**——`test_package` 命中首个目标 `mega-cmd` 即 `exit 0`，本轮**从未尝试** `mega-ls`/`mega-exec`/`mega-cmd-server`；而 L2 对 `mega-ls` 的判失败因不带 runenv 不具证据力（§8.5）。故本条只主张「shebang 与打包面已修复」，**不主张**「68 个命令入口功能级可执行」；后者另受 §8.4 两项运行期限制阻塞（即便补上 runenv 仍需常驻 server）。

### 8.4 运行期平台限制（如实申报，非配方缺陷）

1. **平台 `libcurl/8.5.0` 未启用 TLS**（该包配方 `CURL_USE_OPENSSL=OFF`；`curl-config --features` 无 `SSL`、`--protocols` 无 `HTTPS`）⇒ MEGA SDK `net.cpp:268` 判定后抛异常，`mega-cmd-server` 初始化即中止。证据：`~/.megaCmd/megacmdserver.log` 的 `sdk CRIT curl built without HTTP/HTTPS support. Aborting. [net.cpp:268]`。**属依赖缺陷，已按 W0 规则把 `libcurl/8.5.0` 入表为外部候选**（本包不 block、不硬做）。
2. **CLI↔server IPC 不可用**：套接字为 path-form（`~/.megaCmd/megacmd.socket`），平台**无任何可写目录允许 path-form AF_UNIX bind**（HMDFS EPERM / `/dev/shm` EACCES / `/tmp` EROFS，探针矩阵见 `reports/test-report.md` §5）⇒ `Unable to connect to service: error=2`。修复方向为抽象命名空间套接字（E461 / 探针清单 #8），属上游源码改写，不在本归档范围。

⇒ 本包**可构建、上游单元测试全量真实执行**，但**运行期功能**（登录/传输）在本平台不可用；`test_package` 消费者测试按"包内二进制真实执行"判定并如实标注。该结论与仓库既有平台限制先例一致（如 airspyhf 的"需物理设备 ⇒ 平台限制，记录不阻塞"）。
⇒ 消费者测试的**断言强度上限**与 L2 冒烟步的定性见 §8.3、§8.5：本轮只有 `mega-cmd` 一个目标被真实执行，
不得据此主张 73 个命令入口功能可用，也不得因 `L2=skip` 反过来否认包内二进制可执行。
⇒ **提审状态**：本轮为 `runner: manual` 的**本地 CI 模拟**，远端 GitCode CI 判决与 `/ai review` 结论尚未落地，
`ci-metadata.json` 的 `build_trace.commit` 为 `unknown`、`source_trace.url` 为空（框架生成，未手改）
⇒ **不满足**四件套①④，**不得**据本笔记声称"可以提审"。

### 8.5 最新一轮 W3（2026-09-25 02:29:39）判决与 L2=skip 定性

**判决**（行号均在 `reports/w3-local-ci.log`）：`G0=pass`(23) · `G0e` 通过(25) · `L0=pass`(48/5787) ·
`KC=pass, KC_ERRORS=0`(74/75) · `JC=pass, JC_ERRORS=0`(101) · `L1=pass`(5703-5705, 5788) ·
`L4=pass`(5790) · `L5=pass`(5708, 5791) · `L1e` 反向验证通过(5709-5711) · **`L2=skip`(5712-5785, 5789)** ·
整体 `Success: 1 / Failed: 0 / Pass rate 100.0%` + `All packages built and tested successfully`(5797-5800)。

**L2=skip 的含义**：L2 是 non-blocking 冒烟步，初值即 `skip`，只要 73 个 `bin/*` 里没有任何一个
`--version`/`--help` 成功就保持 `skip` ⇒ 与 `exit_code=0 全绿` 并存属框架预期，既不是失败也不是通过。

**定性 = 判据环境缺陷（不是本包回归，也不只是平台限制）**，三条一手依据：

1. **判据源码**：L2 用 `timeout 15 "$bin_file" --version </dev/null >/dev/null 2>&1` 裸执行包内文件，
   **从不加载 Conan runenv**（复核：`grep -c "LD_LIBRARY_PATH" ci/conan/build_and_test.sh` = **0**），
   并把 stdout/stderr 一起丢弃 ⇒ **日志里不存在 L2 的第一条真实错误**（任何"L2 因为 X 报错而失败"的
   写法都没有日志支撑，这点必须讲明）。
2. **包内容实证**：包目录只有 `bin/` 与 `etc/`（**无 `lib/`、无 `opt/`**），而 `bin/mega-cmd` 内嵌
   `NEEDED` 串 `libcurl.so`、`libuv.so.1`、RUNPATH 串指向不存在的 `opt/megacmd/lib`
   ⇒ 没有 `LD_LIBRARY_PATH` 时加载器必然找不到依赖；68 个包装脚本另需 `PATH`（见 §8.3）。
   Conan runenv 实测注入 `LD_LIBRARY_PATH=<libcurl>/lib:<libuv>/lib`（`test_package/conanrunenv-release-armv8.sh`）。
3. **同轮对照**：同一 package id（`5139148c74021304b15dba88455deab19bb7a0ae`）、同一轮的 `test_package`
   带 runenv 执行 `mega-cmd --version` **成功出 banner**(5692-5699) ⇒ shebang 归一化与重新自签名
   在 W3 的打包路径下**确实生效**，排除"本轮真回归"这一支。

**第二层（属 §8.4 平台限制）**：即便给 L2 补上 runenv，68 个 `mega-*` 包装脚本仍会因需连常驻 server 而失败；
5 个 ELF 则会转为通过。**结论**：L2 不能当"包内二进制不可执行"的证据，也不能反过来用 §8.3 的
`mega-cmd` 成功去主张"73 个入口都可用"。已在 PR 正文「已知限制与未执行/未覆盖的检查」小节如实申报。

**轮次鉴别（本轮 02:20–02:29 的两层门禁分列）**：先 `conan-verify`（= finish Step4 的质量验证，
G1/G0/G2/G3/G4 全 PASS、`conan-verify-report.md` 第 3 行 `**Verdict**: PASS`，报告与
`reports/conan-create.log` mtime 均为 02:24），再由 `finish` step5 跑 **W3 = `ci/conan/build_and_test.sh`**
（结束 02:29:39、`exit_code=0`）。⇒ **编译与测试数字一律取 `reports/w3-local-ci.log`**（本轮判决标记
54 处、baseline 行 5513）；`conan-create.log` 仅 7,371 字节且 `Calling build`/`Building from source`
计数 0，而 verify 报告的 `G4` 带"无法找到程序包 ID"、`L2/L4/L5` 标题虽写 PASS 正文实为
"跳过（无 cache 路径）" ⇒ 这两份件**不足以充当编译与可执行性证据，不作数字来源**。
另：W4 整改前那两轮（09-24 23:46 起）基线读数与本轮逐字一致
（`SUITES_STATIC=8 SUITES_EXECUTED=8 TOTAL=70 PASS=47 FAIL=23`），可作旁证。
另：日志内 worktree 路径写作 `主理-26-megacmd-2.5.2`，与当前 `主理-34-megacmd-2.5.2` 是同一条
（`git worktree move` 改名；改名前生成的 `test_package/conanrunenv-release-armv8.sh` 首行仍写旧路径，可复核）。
---

**编译结束**: 2026-09-25 02:24
**最终状态**: built
