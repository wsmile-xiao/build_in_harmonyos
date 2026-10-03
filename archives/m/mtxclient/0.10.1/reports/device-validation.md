# 真机验证报告 — mtxclient 0.10.1（HarmonyOS PC / aarch64）

> 设备: HarmonyOS localhost / HongMeng Kernel 1.12.0 / aarch64 / clang 15.0.4 / CMake 4.1.2 / conan 2.29.1
> 隔离 job: `$HOME/ohos-users/currentUser/mtxclient-010`（独立 repo + `CONAN_HOME`）
> 执行入口: `ohos-test-runner.sh --mode heavy --try-lock -- zsh ci/conan/build_and_test.sh archives/m/mtxclient/0.10.1`
> 结论: **`Build Summary: Total 1 / Success 1 / Failed 0 / Pass rate 100%`，runner exit 0**
> 最终提交: `archives/m/mtxclient/0.10.1` + 3 个补丁（详见 §5）

## 1. 结果

| 门禁 | 结果 | 说明 |
|------|------|------|
| L0 | ✅ pass | 结构/命名/依赖/门禁全部通过 |
| L1 | ✅ pass | L1a/L1b/L1c 三条证据齐全：`test_package` 被执行、上游 ctest 在 build 阶段执行 |
| L1e | ✅ 破坏性反向验证通过 | 移走 `lib/`+`include/` 后测试确实失败，证明测试真实依赖被测包 |
| L2 | ⏭ skip | 纯库，无 `bin/` |
| **L4** | ⚠️ warn | **误报**，见 §4 |
| **L5** | ❌ fail | **环境限制**（设备无 ELF 读取器），见 §3 |

`conan create` 全流程成功：下载（经 gh-proxy 镜像）→ 打补丁 → configure → 编译 → 链接 → 上游 ctest → 打包 → `test_package` 构建+运行 → 下游消费者验证。

## 2. 上游测试执行情况

`ctest` 注册 15 个用例；`patches`+`CTestCustom.cmake.in` 排除 6 个必须真实 Synapse 的用例后，
**实际执行并通过 9 个离线用例**：

```
Test #1..#9: Utilities, Identifiers, Errors, CryptoStructs, StateEvents,
             RoomEvents, VoIPEvents, Responses, Requests   → 9/9 通过
```

被排除（不执行，仍构建）的 6 个：`BasicConnectivity`、`ClientAPI`、`MediaAPI`、`Encryption`、`Devices`、`Pushrules`
—— 上游 `tests/meson.build` 标 `suite: network`，需要 `.ci/synapse` 提供的真实 homeserver。

`test_package`（消费者视角）**39 项断言全部通过**：

```
checks=39 failures=0
MTXCLIENT_TEST_PACKAGE_OK
```

## 3. L5 失败是环境限制，不是库缺陷（关键证据）

L5 门禁用 `readelf -d` 读 `DT_SONAME`：

```sh
# ci/conan/build_and_test.sh:1447
ELF_INFO=$(readelf -d "$so_file" 2>/dev/null || true)
SONAME_VAL=$(echo "$ELF_INFO" | grep '(SONAME)' | sed 's/.*\[\(.*\)\].*/\1/' || true)
if [ -z "$SONAME_VAL" ]; then  → fail
```

**本设备上 `readelf` 根本不存在**，因此 `ELF_INFO` 恒为空、L5a/L5b 恒失败：

```
readelf        missing
llvm-readelf   missing
llvm-readobj   /storage/Users/currentUser/usr/local/bin/llvm-readobj   ← 唯一可用的 ELF 读取器
objdump        missing
```

用设备上唯一的读取器验证**库本身是正确的**：

```
$ llvm-readobj --dynamic-table p/lib/libmatrix_client.so
  0x000000000000000E SONAME  Library soname: [libmatrix_client.so.0.10.1]
```

两个打包文件名（`libmatrix_client.so` 与 `libmatrix_client.so.0.10.1`）都带同一个 SONAME，
`test_package` 能正常加载并跑完全部 39 项断言 —— 这本身就证明 SONAME 是对的。

> 影响面：该设备上**任何**产出 `.so` 的包都会得到 `L5_RESULT=fail: soname_gate_failed`。
> 若要让 L5 在此设备可用，需在设备上提供 `readelf`（或让门禁回退到 `llvm-readobj`）。

L5c 的 `IMPORTED_NO_SONAME TRUE` 是 CMake 生成 `MatrixClientTargets-release.cmake` 时的标记；
`COMPILE_DEFINITIONS`/链接在 `test_package` 中实测正常（下游消费者构建+运行通过），
说明该标记在此场景下未造成实际影响。

## 4. L4 告警是子串误报

L4 用 `grep -rlE '(strcpy|sprintf|gets|strcat)\b' patches/` 扫描补丁。
补丁是**散文式 unified diff**，正文里出现 `targets`、`widgets` 之类的词就会命中 `gets`：

```
0002-cmakelists-gtest-targets.patch: 4:gets  6:gets  8:gets  19:gets
0003-cmakelists-force-soname.patch: 15:gets
```

补丁正文里没有任何 C 危险函数调用（补丁只改 `CMakeLists.txt` 的 CMake 语法）。
属于扫描规则对"补丁正文含英文散文"的误报，不阻塞构建。

## 5. 真机暴露并修复的问题（本机静态验证未能发现）

按发现顺序，全部在真机 `conan create` 中暴露：

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | `ci/conan/build_and_test.sh:22: command not found: ^M` | 快照传输后脚本为 CRLF；`/bin/sh` 不是 bash，`$'\r'` 不生效 | 主机侧先做 LF 规范化再打包（避免在 HMDFS 上全树扫描） |
| 2 | `Invalid build timeout config at line 3: 10800` | 同上，配置行尾带 `\r`，awk 取到 `10800\r` | 同上 |
| 3 | `Could not find a package configuration file provided by "olm"` | **`generators = "CMakeDeps", "PkgConfigDeps"` 只写在注释里，没有作为类属性声明** → Conan 只生成 toolchain，不生成任何 `*-config.cmake`/`.pc` | 补上类属性 |
| 4 | `'operator<=' cannot be the name of a variable or data member` | `CMakeToolchain` 的 `CppStdBlock` 用 profile 的 `compiler.cppstd=17` 发出**普通** CMake 变量，普通变量优先级高于 `tc.cache_variables` | `generate()` 中 `self.settings.compiler.cppstd = "20"`，让工具链发 `-std=c++20` |
| 5 | `Target "client_api" links to GTest::GTest but the target was not found` | gtest 1.13 改名、1.14 删除旧目标名 | 补丁 0002 改用 `GTest::gtest` / `GTest::gtest_main` |
| 6 | `GTest::gtest` 也找不到（CMakeDeps 只给 `gtest::gtest`，无 `gtest_main`） | gtest 配方只声明 `cpp_info.libs=["gtest"]`，CMakeDeps 不导出 `gtest_main` | `generate()` 里把 `GTest_DIR` 指向包内自带的 `GTestConfig.cmake`（该文件同时导出两个目标） |
| 7 | `Could not find PkgConfig`（潜在） | 设备无 `pkg-config`/`pkgconf` | `tool_requires("pkgconf/3.0.6")` + 固定 `PKG_CONFIG_EXECUTABLE` |
| 8 | `Error loading shared library libspdlog.so.1.17 / libcurl.so ...` | `cmake.test()` 走 `cmake --build --target test`，不套 run 环境 | 改为 `self.run("ctest ...", env="conanrun")` |
| 9 | `CTEST_CUSTOM_TESTS_IGNORE: Unknown CMake command` | 它是**变量**不是命令，必须 `set()` | 修正 `CTestCustom.cmake.in` |
| 10 | `'CMake' object has no attribute 'build_folder'` | Conan 2.x `CMake` 无该属性 | 改用 `self.build_folder` |
| 11 | `Error loading shared library libmatrix_client.so` | 被测库自身不在 run 路径上 | 运行期把构建目录加入 `LD_LIBRARY_PATH` |
| 12 | test_package `'nlohmann/json.hpp' file not found` | nlohmann_json 是 header-only，**Conan 不为它建包节点**，`package_info()` 无法把其 include 目录转达到消费者 | `test_package` 显式 `requires("nlohmann_json/3.12.0")` |
| 13 | test_package `'spdlog/fmt/bundled/format.h' file not found` | 打包的 spdlog 用 external fmt 编译，但配方未声明接口宏 | `cpp_info.defines` 补 `SPDLOG_FMT_EXTERNAL`/`SPDLOG_COMPILED_LIB`/`SPDLOG_SHARED_LIB` |
| 14 | 库无 `DT_SONAME`、安装后无版本名、导出 `IMPORTED_NO_SONAME TRUE` | **OHOS 上 CMake 不实现 VERSION/SOVERSION**：即便属性正确、目标确为 `SHARED_LIBRARY`，链接行仍无 `-soname`、install 也只产出未版本化文件名（已用最小复现工程证实） | 补丁 0003 显式传 `LINKER:-soname,...`；`package()` 再物化 soname 文件名 |

其中 #3、#4、#14 是**本机静态验证无法发现**的：分别需要真实 Conan 生成器行为、真实工具链标准实现、真实 CMake 平台实现。

## 6. 下游消费者（test_package）实测输出

```
mtxclient test_package
ok: user localpart / user hostname / room hostname / v12 room id ...
ok: mxc server, mxc media id, is_number, random_token, query_params, url_encode
ok: bin2base64 RFC 4648 vector, base642bin RFC 4648 vector
ok: http client server host (scheme stripped), default https port, reconstructed server url
ok: AES-CTR ... / HMAC-SHA256 / PBKDF2 / HKDF / CURVE25519 / SSSS / encrypt_file
ok: Text event ... / Login response ...
checks=39 failures=0
MTXCLIENT_TEST_PACKAGE_OK
```

## 7. 设备环境备注（供后续会话）

- 工具链：`clang`/`clang++`/`cmake`/`ninja`/`python3`/`zsh` 均在 `$HOME/usr/local/bin`，
  **不在** `ci/conan/profiles/ohos-aarch64` 写死的 `/data/service/hnp/bin`；
  该 profile 在此设备不可用，需指向 `$HOME/usr/local/bin`（本任务在隔离 job 内改了副本，未动仓库）。
- `conan`：无 console script，实际入口 `/storage/Users/currentUser/.local/bin/conan`（2.31.1）与
  shadow 环境 `$HOME/ohpc-ci-shadow/python-user/bin/conan`（2.29.1，CI 使用）。
- **无 `readelf`/`llvm-readelf`/`objdump`**，只有 `llvm-readobj`（见 §3）。
- `/tmp` 只读：所有远端脚本需 `export TMPDIR=...`，且不能依赖 here-doc。
- `make -j` 的 jobserver FIFO 会报 `mkfifo ... Operation not permitted`，但构建继续并成功（已知平台行为）。
- 设备负载长期在 20 左右，不代表繁忙；判断繁忙看 runner 锁与活跃构建进程。
