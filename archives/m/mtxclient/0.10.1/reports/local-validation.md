# mtxclient 0.10.1 — 本机（Windows 前置阶段）验证报告

> 时间: 2026-09-29
> 范围: 所有不需要 HarmonyOS 设备的静态与半动态验证 + 设备只读探针
> 结论: 配方、补丁、test_package 与依赖声明均已逐项验证；W0 依赖全部已发布；
> **未做设备构建**（设备在会话期间处于他人构建负载下，未取到空闲窗口）

本机没有 OHOS 工具链与 CMake，因此本报告只覆盖可离线验证的部分，另附设备只读探针结果。
所有结论都附了可复现命令。

> ⚠️ **已修订**：初版 §2 用 `conan download` 的退出码判断依赖发布状态，得出「coeurl 未发布」的
> 错误结论。修订后改用 `conan graph info` 读 `binary` 字段，详见 §2。

## 1. 源码与校验值

| 项 | 值 |
|----|-----|
| URL | `https://github.com/Nheko-Reborn/mtxclient/archive/refs/tags/v0.10.1.tar.gz` |
| 实测 sha256 | `203be46a08e1dc6cfc068d0911f3b09976f48e4cc4302c3517b9c0f4e53631e3` |
| conandata.yml 声明 | 同上（一致） |
| 解包体积 | 636,035 字节 tar.gz |
| 上游版本自证 | `CMakeLists.txt` `project(matrix_client VERSION 0.10.1 ...)`、`CHANGELOG.md` `## [0.10.1] -- 2025-08-02` |

```powershell
python -c "import hashlib,io; print(hashlib.sha256(io.open('mtxclient-0.10.1.tar.gz','rb').read()).hexdigest())"
# 203be46a08e1dc6cfc068d0911f3b09976f48e4cc4302c3517b9c0f4e53631e3
```

## 2. W0 依赖发布检查（R36 / R35）—— 全部通过

### 2.1 方法学：为什么不能用 `conan download` 的退出码

本次会话先用了 `conan download <ref> -r=ohpcd --only-recipe` 的**退出码**，得到错误结论。复测发现：

| 观测 | 含义 |
|------|------|
| 打印 `packages: No packages found for this revision` 但 **exit 0** | 远端只匹配到 recipe、没有匹配当前 profile 的 binary —— 退出码仍为 0 |
| 打印 `ERROR: error:system acceleration policy not enabled` 且 exit≠0 | 网关/网络瞬时抖动（同一 ref 重试可成功） |

两种信号都不可靠，**唯一可信的是 `conan graph info` / `conan install` 的节点 `binary` 字段**。

```sh
conan graph info --requires=<ref> \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<build-profile> -f=json
# 读 nodes[*].binary：Cache / Download = 有制品；Missing = 没有
```

> 附带发现：`ci/scripts/preflight_check.sh` 与 `scripts/ohc/preflight.py` 都走制品仓 search API，
> 而 R35 指出该 API 对 binary 返回不完整（会出现"显示没有但实际已上传"）。
> 两者都不能替代 `conan graph info`。

### 2.2 逐项结果（`binary` 字段实测）

| # | 依赖 | 版本 | binary | 备注 |
|---|------|------|--------|------|
| 1 | openssl | 3.5.6.1 | Cache | — |
| 2 | olm | 3.2.16 | Cache | — |
| 3 | nlohmann_json | 3.12.0 | Cache | — |
| 4 | coeurl | 0.3.2 | **Cache** | 制品在 ohpcd；归档目录尚未合入 main |
| 5 | re2 | 2024-04-01 | Cache | 带出 abseil-cpp/20260107.1（Cache） |
| 6 | libcurl | 8.5.0 | Cache | — |
| 7 | libevent | 2.1.13 | Cache | — |
| 8 | spdlog | 1.17.0 | Cache | 带出 fmt/12.2.0（Cache） |
| 9 | fmt | 12.2.0 | Cache | — |
| 10 | gtest | 1.17.0 | Cache | test_requires |
| 11 | pkgconf | 3.0.6 | Cache（host） | tool_requires，见 §7 |

**结论：11/11 可用，无 W0 阻塞。**

### 2.3 依赖图解析（无冲突）

```sh
conan graph info archives/m/mtxclient/0.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<build-profile> -f=json
```

结果：15 个节点，`graph.error = None`，无节点级 error。
唯一非 `Cache`/`Skip` 的是 `mtxclient/0.10.1` 自身（待构建），以及 build 上下文的
`pkgconf/3.0.6`（在 Windows build profile 下显示 `Missing`，因为它的制品是 OHOS/aarch64；
设备上 `-pr:b` 同为 ohos-aarch64 时解析为已发布制品）。

版本一致性：coeurl 0.3.2 自身的 requires（libcurl/8.5.0、spdlog/1.17.0、libevent/2.1.13、fmt/12.2.0）
与本配方的直接引用完全同版，无版本冲突。

## 3. 构建系统分析结论

| 结论 | 证据 |
|------|------|
| CMake 构建（另有无用的 meson.build） | 仓库同时有 `CMakeLists.txt`（516 行）与 `meson.build`；本配方走 CMake |
| 必须 C++20 | `include/mtx/identifiers.hpp:75` 用 `<=>` + `std::strong_ordering` |
| **5 个依赖走 pkg-config** | `CMakeLists.txt:137`（re2）、`:147/:150`（libevent_core/pthreads）、`:163`（libcurl）、`:191`（coeurl>=0.3.0）；补丁 0002 再新增 gtest_main |
| 其余走 find_package CONFIG | `OpenSSL 1.1.0`、`olm 3.2.7`、`nlohmann_json 3.11.0`、`spdlog 1.0.0`、`GTest` |
| re2 是真依赖 | `lib/structs/pushrules.cpp:6` `#include <re2/re2.h>`，`:451-466` 用 `re2::RE2` |
| 上游 toolchain.cmake 不干扰 Conan | `CMakeLists.txt:4-10` 设 `CMAKE_TOOLCHAIN_FILE` CACHE；该文件仅 3 行（C++ 标准/PIC）；Conan 以命令行 `-DCMAKE_TOOLCHAIN_FILE=` 注入（`conan/tools/cmake/cmake.py`），命令行优先且 `set(...CACHE...)` 不覆盖已有 cache 项 |
| 上游测试 15 个，其中 6 个需真实 Synapse | `tests/meson.build` `suite: network` 6 个 / `suite: nonetwork` 9 个；CMakeLists 末尾 15 个 `add_test()` |

## 4. 补丁验证

在**全新下载**的源码副本上顺序 apply（不是复用已改过的目录）：

```sh
git -c core.autocrlf=false apply --check patches/0001-...patch   # exit 0
git -c core.autocrlf=false apply       patches/0001-...patch     # exit 0
git -c core.autocrlf=false apply --check patches/0002-...patch   # exit 0
git -c core.autocrlf=false apply       patches/0002-...patch     # exit 0
```

合并改动量：`1 file changed, 18 insertions(+), 33 deletions(-)`（CMakeLists.txt）。
自检：文件内不再出现 `Olm::Olm`，出现 `olm::olm`；`GTest::gtest_main` 恰好 15 处；
`GTest::GTest` / `GTest::Main` 残留 0 处。

补丁只改 `CMakeLists.txt`（构建系统），未改任何源文件，符合 R6。

## 5. CMakeDeps / PkgConfigDeps 产物与 mtxclient 探测方式逐项对齐

本机用 `conan install`（宿主 profile = ohos-aarch64）实际生成了一次依赖产物
（coeurl 曾用同 ABI 的本地占位包替代以确认文件名与目标名；coeurl 0.3.2 的真实制品随后已在
ohpcd 确认存在），核对结果：

| mtxclient 的探测 | 需要 | 实测生成 | 结论 |
|------------------|------|----------|------|
| `find_package(OpenSSL 1.1.0 REQUIRED)` + `OpenSSL::Crypto/SSL` | `OpenSSLConfig.cmake` + 该两目标 | `OpenSSLConfig.cmake`，`OpenSSL::Crypto` / `OpenSSL::SSL` | ✅ |
| `find_package(olm 3.2.7 REQUIRED)`（补丁后）+ `olm::olm` | `olm-config.cmake` + `olm::olm` | `olm-config.cmake`，`olm::olm` | ✅（补丁 0001 必要） |
| `find_package(nlohmann_json 3.11.0 CONFIG REQUIRED)` | `nlohmann_json-config.cmake` | `nlohmann_json-config.cmake`，`nlohmann_json::nlohmann_json` | ✅ |
| `find_package(spdlog 1.0.0 CONFIG)` + `spdlog::spdlog` | `spdlog-config.cmake` | `spdlog-config.cmake` | ✅ |
| `pkg_check_modules(re2 REQUIRED IMPORTED_TARGET re2)` | `re2.pc` | `re2.pc`（含 `Requires: abseil-cpp`） | ✅ |
| `pkg_check_modules(libevent_core/libevent_pthreads ...)` | 两个 `.pc` | `libevent_core.pc`、`libevent_pthreads.pc` | ✅ |
| `pkg_check_modules(libcurl REQUIRED IMPORTED_TARGET libcurl)` | `libcurl.pc` | `libcurl.pc` | ✅ |
| `pkg_check_modules(coeurl REQUIRED IMPORTED_TARGET coeurl>=0.3.0)` | `coeurl.pc` | coeurl 0.3.2 的 meson `pkg.generate` 产出 `coeurl.pc`；PkgConfigDeps 会按包目录重新生成，`version` 来自包版本 0.3.2（满足 `>=0.3.0`） | ✅（设备构建时最终确认） |
| `find_package(coeurl CONFIG REQUIRED)`（coeurl_DIR 分支）+ `coeurl::coeurl` | `coeurl-config.cmake` + `coeurl::coeurl` | 实测占位包生成 `coeurl-config.cmake` + `coeurl::coeurl` | ✅（文件名/目标名与 conan 包名一致） |
| `find_package(GTest REQUIRED)` | CMakeDeps 生成 `gtest-config.cmake` | 实测存在；CMake 同时搜索 `<Name>Config.cmake` 与 `<name>-config.cmake`（`cmFindPackageCommand.cxx:1389,1392`），名字可命中 | ✅ 包名无需补丁 |
| 测试目标 `GTest::GTest` / `GTest::Main` | gtest 1.17 只提供 `GTest::gtest` / `GTest::gtest_main` | 包内 `lib/cmake/GTest/GTestTargets.cmake` 只有小写目标 | ❌ 必须补丁 0002 |
| `pkg_check_modules(gtest_main ...)`（补丁后） | `gtest_main.pc` | 包内自带 `lib/pkgconfig/gtest_main.pc`（上游 `INSTALL_GTEST=ON`） | ✅（补丁 0002 依据） |

关键区分：**包名**大小写不是问题（CMake 有小写回退），**目标名**才是问题 —— 所以
补丁 0001 处理 olm 的目标/包名，补丁 0002 只处理 gtest 的目标来源。

## 6. 本机 CI 门禁复刻（48 项，全通过）

按 `ci/conan/build_and_test.sh` 的 L0a-L0e / L0g-L0i / R32 / R33 / R34 / R38 逻辑在本机复刻执行：

```
checks: 48  failed: 0
```

覆盖：目录结构（L0a/b/c/e）、`test()` 与 `self.run()`（L0d）、非假测试（L1d 的正则
`self\.run.*(echo|print|true)`）、无硬编码 remote（L0g）、sha256 格式与真实性（L0g）、
`self.run()` 内无裸 `${CC}` 等（L0h/R33）、patch 列表格式/命名/描述/类型（L0f/L0i）、
`settings.os` 无 `== "Linux"`（R32）、库类型无 `commands.json`（R38）、
test_package 实质调用被测包 API（24 处 `mtx::` 引用）、MANIFEST `assertion_count>0`、
无 TODO/FIXME 占位符、无 `__pycache__`/`.pyc` 残留、全部文本文件 LF + 无 BOM + 结尾换行。

## 7. 设备只读探针结果

SSH 可达（`currentUser@frp-tip.com:56267`，密钥 `ohos_pc_codex_ed25519`）：

```
HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP ... aarch64 Toybox
HOME=/storage/Users/currentUser
```

| 探测项 | 结果 | 影响 |
|--------|------|------|
| `git` | `/data/service/hnp/bin/git` | 需显式设 PATH |
| `cmake` / `ninja` / `python3` / `zsh` | `$HOME/usr/local/bin/*`（python3 = 3.12.9） | 需显式设 PATH |
| `pkg-config` / `pkgconf` | **都不存在**（PATH、hnp/bin、/usr/bin 均无） | ❗ 必须由 tool_requires 提供，见 §9 |
| `conan` | **无 console script**；`python3 -m conan` 失败；`import conan` = **2.31.1** | 版本与文档基线 2.29.1 不同，入口需确认 |
| runner | `$HOME/bin/ohos-test-runner.sh`、`ohos-prepare-isolated-conan-job.sh` 存在 | 可用 |
| `run-ohos-shadow-ci.sh` | `$HOME/bin` 下**不存在**（`$HOME/validation/run-ohos-shadow-ci-local.sh` 有） | 入口需确认 |
| `/proc/loadavg` | `21.77 23.92 24.02` | 负载高 |
| 并发任务 | `ohos-test-runs/` 下有 `tiger-3.2.4-*`、`medusa-2.3-*` | 他人在跑 |
| fork 能力 | 多次 `sh: can't fork - try again`、`/bin/grep: Out of memory` | 资源紧张 |
| runner 锁 | 最近一次 `tiger-...-build-direct-...` 是 `echo hi` 探针，rc=0 | 锁已释放 |

按工作流 §5 错峰规则与本轮约束（未明确拿到空闲窗口），**本轮未在设备上执行构建**。

## 8. test_package 断言清单（36 项）

`test_package.cpp` 中 `check()` / `check_eq()` 调用点实测 36 个（脚本统计，排除定义本身）：

| 分组 | 数量 | 内容 |
|------|------|------|
| check_identifiers | 6 | User/Room 解析、hostname/localpart、v12 无服务器名房间 id、json 往返、operator== |
| check_client_utils | 9 | MXC URI、is_number、random_token、query_params、url_encode、RFC 4648 base64 双向 |
| check_http_client | 2 | `mtx::http::Client` 构造 + `server()`、access_token getter |
| check_crypto | 13 | AES-CTR 往返、HMAC-SHA256、PBKDF2、HKDF、libolm CURVE25519、SSSS 往返、encrypt_file/decrypt_file 往返 |
| check_json_structs | 6 | Text 事件序列化/msgtype/往返、Login 响应反序列化 |

所有用到的 API 都已逐个核对上游头文件签名与命名空间：`mtx::identifiers::parse<T>` /
`localpart()` / `hostname()`（`include/mtx/identifiers.hpp:25,27`）、`Client::server()`
（`include/mtxclient/http/client.hpp:226`，注意不是 `homeserver()`）、`Client::set_server`
会剥掉 `https://` 前缀（`lib/http/client.cpp:163-194`，故期望值 `example.com`）、
`mtx::events::msg::Text::msgtype` 是 `std::string`（`include/mtx/events/messages/text.hpp:25`）、
`Login::user_id` 是 `mtx::identifiers::User`（`include/mtx/responses/login.hpp`）、
`mtx::crypto::EncryptedFile` 在 `include/mtx/common.hpp:88`（已显式 include）。

`ClientPrivate` 只有一个 `coeurl::Client` 成员，构造函数不发起网络 I/O，因此
构造 `mtx::http::Client` 在离线环境是安全的。

## 9. 未验证项（需要设备空闲窗口）

| 项 | 原因 |
|----|------|
| `conan create` 完整构建 | 设备处于他人构建负载下，未取到空闲窗口 |
| 9 个 nonetwork 上游用例的实际通过率 | 同上 |
| 15 个测试二进制能否在 clang 15 / libc++ / C++20 下编译通过 | 同上（本机无 OHOS 工具链） |
| 6 个 network 用例 | 需要真实 Synapse，且 curl 无 TLS |
| 安装后的 `MatrixClient::MatrixClient` CMake 包可被消费 | 需要先安装产物 |
| `.so` 的 SONAME/RPATH/NEEDED 与签名 | 需要设备 |
| `pkgconf/3.0.6` 作为 build 上下文依赖在设备上的解析 | 本机 build profile 是 Windows，节点显示 `Missing` 属预期 |

> 注：设备缺 pkg-config 一事**不是**未验证项 —— 已实测确认缺失，并已在配方中通过
> `tool_requires("pkgconf/3.0.6")` + `PKG_CONFIG_EXECUTABLE` 固定路径解决；
> 其实际生效仍需设备构建验证。

## 10. 复现命令汇总

```powershell
# sha256
python -c "import hashlib,io; print(hashlib.sha256(io.open('mtxclient-0.10.1.tar.gz','rb').read()).hexdigest())"

# W0 依赖（R35 正确方式：读 binary 字段，不要用 conan download 的退出码）
conan graph info --requires=coeurl/0.3.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<build-profile> -f=json

# 依赖图（无冲突证明）
conan graph info archives/m/mtxclient/0.10.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<build-profile> -f=json

# 补丁（顺序 apply，须全部 exit 0；建议对全新下载的源码做）
git -c core.autocrlf=false apply --check archives/m/mtxclient/0.10.1/patches/0001-cmakelists-lowercase-olm-package.patch
git -c core.autocrlf=false apply --check archives/m/mtxclient/0.10.1/patches/0002-cmakelists-gtest-targets.patch

# 本机门禁复刻
python _w0probe/local_gates.py
```
