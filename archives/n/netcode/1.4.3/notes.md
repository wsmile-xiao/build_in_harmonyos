# netcode 1.4.3 适配笔记

## 编译环境

- 构建系统：CMake（上游原生支持，`NETCODE_BUILD_TESTS` / `NETCODE_SYSTEM_SODIUM` 开关）
- 适配日期：2026-09-10
- 编译器：clang 15（HarmonyOS PC aarch64 真机，conan profile `ci/conan/profiles/ohos-aarch64`）
- 平台：HarmonyOS PC aarch64（原生构建，非交叉）
- 状态：built（配方已完成，真机预检待 HMBS 后台执行）

## 编译步骤

```bash
# 主包（conan create 自动执行）
cmake -S . -B build -DBUILD_SHARED_LIBS=OFF -DNETCODE_BUILD_TESTS=ON -DNETCODE_SYSTEM_SODIUM=OFF
CMAKE_BUILD_PARALLEL_LEVEL=1 cmake --build build --target netcode
CMAKE_BUILD_PARALLEL_LEVEL=1 cmake --build build --target netcode_test  # 仅库+上游 runner，真机 OOM 精简（跳过 5 个示例）
ctest -V --output-on-failure        # 上游 46 个 RUN_TEST，输出 HMBS_UPSTREAM_TEST_RESULT
cmake --install build --prefix <package_folder>

# 消费者验证（test_package 自动执行）
cmake -S test_package -B build -DCMAKE_PREFIX_PATH=<package_folder>
cmake --build build
ctest --output-on-failure           # test_netcode，输出 HMBS_TEST_PACKAGE_RESULT
<package>/res/upstream-test/test    # 上游套件重跑（防缓存命中跳过 build），输出 HMBS_UPSTREAM_TEST_RESULT
```

## 上游测试审计（v1.4.3 源码实测）

- 测试驱动：`test.cpp`（48 行）编译 `netcode.c`（`NETCODE_ENABLE_TESTS`）并调用 `netcode_test()`。
- `netcode_test()` 内共 46 个 `RUN_TEST`（源码正则统计，含 `#if NETCODE_PACKET_TAGGING` 的
  `test_packet_tagging`；该宏在非 MinGW 平台默认为 1，OHOS 下 46 个全量运行）。
- 划分：单元测试 27（加解密向量、队列、端序、地址、序列号、connect/challenge token、
  各包编解码、加密管理、重放保护、运行时守卫、初始化、client/server 创建与错误、网络模拟器、
  服务端重启序号、包 tagging）；集成测试 19（client/server 建联 IPv4/IPv6/双栈、保活、
  多客户端/多服务端、6 种错误路径、双侧断开、断开原因、重连、超时禁用、loopback）。
- 失败语义：`check()` 失败触发 assert/退出，无静默跳过；全过打印 `*** ALL TESTS PASSED ***`。
- 证伪措施：配方校验测试二进制非空（>1KB）、输出非空、46 个用例名与源码审计集合求交、
  `ALL TESTS PASSED` 横幅与退出码三者同时成立才判通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试二进制在 `conan create` 缓存命中时不执行 | `--build=missing` 下包已缓存则跳过 `build()`，`HMBS_UPSTREAM_TEST_RESULT` 无证据 | `package()` 把 `bin/test` 持久化到 `res/upstream-test`，`test_package` 每次重跑并输出标记（pagodacf R26 同类教训） |
| 2 | `ctest` 默认隐藏通过用例输出，无法计数 46 个子用例 | ctest 非 `-V` 模式只打印 `Passed` 汇总 | `build()` 用 `ctest -V --output-on-failure` 并全量打印日志，逐行计数 |
| 3 | `test()` 需 `self.run()` 显式调用（L0d/PF3） | 门禁字面检查 `self.run` | 消费者二进制与日志捕获均走 `self.run(..., stdout=f)`，再用 Python 解析 TAP |
| 4 | 真机 compile 阶段 `/bin/sh: Out of memory` | `NETCODE_BUILD_TESTS=ON` 默认全量构建 5 个示例 + 库 + unity 测试 TU，峰值内存超真机限制 | `build()` 仅构建 `netcode` + `netcode_test` 两个必需 target 并强制单作业（`CMAKE_BUILD_PARALLEL_LEVEL=1`），上游 46 用例仍经 ctest 全量运行 |

## 源码修改

无源码修改，无补丁。`conandata.yml` 仅官方 GitHub tag 归档 URL + sha256。

## 依赖版本

无外部依赖。加密由上游自带的 libsodium 子集（`sodium/sodium.c`，`NETCODE_SYSTEM_SODIUM=OFF`）
提供，随包静态编译，不占用系统库路径（非 R26 系统同名库）。

## 验证结果

- 配方静态检查：`conanfile.py` / `test_package/conanfile.py` 通过 `ast.parse` 语法校验（本机）。
- 真机 `conan create`（含上游 46 项 + 消费者 4 项 TAP）：待 HMBS 后台预检执行，数字回填 PR 正文。
- 安装产物：静态 `libnetcode.a`（或按选项的共享库）、`netcode.h`、`LICENCE`（licenses/）、
  上游测试 Runner（`res/upstream-test/test`，仅供证据重跑）。

## 注意事项

- netcode 单线程设计（`netcode_init`/`netcode_term` 全局状态），多线程调用需自行加锁。
- 上游集成测试使用真实 UDP 回环 socket；若真机回环受限导致个别集成用例失败，
  按实际日志修配方/补丁，不删测试、不改通过率口径。
- `NETCODE_PACKET_TAGGING` 在 OHOS 下保持上游默认开启（1），与上游 CI 一致。
