# cpp-httplib 0.41.0 HarmonyOS 适配说明

## 交付范围

- 上游：`yhirose/cpp-httplib` 正式标签 `v0.41.0`
- 目标：HarmonyOS 6.0 PC，aarch64/armv8，Clang 15，libc++；本地
  x86_64 虚拟机仅作为交叉编译宿主与补充运行环境
- 形态：C++11 header-only；安装 `httplib.h` 与上游 CMake 导出
- 消费接口：`find_package(httplib CONFIG REQUIRED)`、`httplib::httplib`
- 消费依赖：无
- 关闭能力：OpenSSL、wolfSSL、Mbed TLS、Zlib、Brotli、Zstd 与 compiled-library 模式

## 来源与门禁

- 标签提交：`073b58796205b928b61f4cae89ab4130b7f1aee0`
- 官方归档：`https://github.com/yhirose/cpp-httplib/archive/refs/tags/v0.41.0.tar.gz`
- SHA-256：`6d38a6b74ea33ac3133b8352f2b55b557c1d42f36e1ed0c01f852e3218329d39`
- 头文件版本：`CPPHTTPLIB_VERSION == "0.41.0"`
- `lang-preflight`：`task=cpp`、`detected=cpp`，CMake 项目，C++ 主体占 95%
- `prescan --no-writeback`：识别到证书默认路径、符号链接、bash shebang、glibc 条件与 `pthread_kill` 风险；均在测试阶段核验，没有改写知识库。
- W0：`gtest/1.17.0` 与 `curl/8.15.0.1` 配方均已发布；`cpp-httplib/0.41.0`
  未发布。交付配置关闭可选 TLS/压缩能力并保持零消费依赖，确定性测试使用
  GTest；单个外部 libcurl 互操作用例不属于该特性配置。

## 上游测试清点

源码共有 700 个 GoogleTest 声明：

- `test/test.cc`：662
- `test/test_proxy.cc`：22
- `test/test_thread_pool.cc`：9
- `test/test_websocket_heartbeat.cc`：5
- `test/test_benchmark.cc`：2

上游正式 CMake 测试入口构建 `test/test.cc`、`include_httplib.cc` 以及 fuzz
冒烟目标。当前无 TLS/压缩特性的 Linux 配置发现 496 个 GoogleTest 实例与
1 个 fuzz CTest，共 497 项；平台、编译器和可选特性条件会使源码声明数高于
实际实例数。

明确排除项：

- `Expect100ContinueTest.ServerClosesConnection` 是依赖外部 libcurl 的互操作
  用例；当前零依赖、无 TLS/压缩交付配置不启用该额外测试依赖。
- 15 个名称含 `_Online` 的用例访问外部主机，不作为确定性本地 CI；其余
  482 个 CTest 在 Linux 原生环境全量执行。
- HarmonyOS 原生 CI 的工作目录位于 HMDFS；路径型 Unix domain socket
  节点无法在该文件系统中创建。CI #44435 中，使用同一
  `./httplib-server.sock` fixture 的 `UnixSocketTest.pathname`、
  `UnixSocketTest.PeerPid`、`UnixSocketTest.HostHeaderAutoSet` 全部失败，
  而相邻的抽象地址 `UnixSocketTest.abstract` 通过，其他 478 个 GoogleTest
  实例和 fuzz CTest 也通过。因此 OHOS 仅排除这 3 个路径型 socket 用例，
  修复后的确定性集合为 479 项；Linux 仍执行 482/482。
- `test_proxy.cc` 需要代理服务拓扑，`test_thread_pool.cc` 与
  `test_websocket_heartbeat.cc` 没有接入上游正式 CMake 测试目标；
  `test_benchmark.cc` 是性能基准，不属于正确性回归。它们没有被计入已执行数。
- TLS 与压缩相关实例因本包明确的零依赖交付范围而未启用。

## 适配内容

两个补丁只修改上游测试接线和测试夹具：

1. 显式载入 CMake `GoogleTest` 助手，使 Conan GTest 的官方 CMake 导出可用于
   `gtest_discover_tests`。
2. 增加 `HTTPLIB_TEST_WITH_CURL`，在当前零依赖特性配置中关闭唯一 libcurl
   互操作用例。
3. 回移上游主线的测试稳定性修复：临时单响应服务器先读完 HTTP 请求头再
   发送响应并关闭，避免未读请求数据使内核发送 RST、偶发丢弃已发送响应。

补丁不修改 `httplib.h`、HTTP 行为、ABI 或安装接口。

## 验证摘要

- Linux 原生 Conan：GCC 13.3、Conan 2.29.1；上游确定性测试 482/482；
  消费者版本、URL 解析、GET、POST、状态、头与正文检查通过。
- HarmonyOS 原生 CI #44435：观察到 479/482 通过；修复仅按上述 HMDFS
  能力边界排除 3 个路径型 Unix socket 用例，形成 479 项确定性集合。该次 CI
  中抽象 AF_UNIX 用例已经实际通过；修复后的远端复跑结果另以 CI 为准。
- HarmonyOS 原生 CI #44482：在源码阶段发现提交前的补丁空白规范化误删了
  unified diff 必需的空白上下文标记，Conan 报 `patch stream is incomplete`。
  已恢复仓库生成器的原始补丁字节，并用 Conan `source()` 对官方源码重新下载、
  解压和应用两个补丁，解析与应用均通过。
- HarmonyOS 原生 CI #44501：正式 `OHOS/armv8` profile 已完成源码、补丁、
  上游 479/479、打包与安装；随后专属消费者因错误的 `__x86_64__` 编译门禁
  失败。该门禁来自把本地宿主误当交付目标，现已改为 `__aarch64__`/ARM64。
- 先前 OHOS x86_64 构建与 HDC 结果只作为补充兼容性证据：官方纯 API 子集
  101/101、fuzz 冒烟和专属 API 消费者通过，但不再作为 aarch64 交付验收。
- 本地 aarch64 交叉 Conan：Windows x86_64 宿主、HarmonyOS SDK 26.0.0、
  OHOS 6.0 armv8、Clang 15、libc++；上游主测试、fuzz、包安装、普通消费者和
  HarmonyOS 专属消费者均编译链接通过。四个可执行文件经 `llvm-readelf -h`
  核验均为 ELF64 AArch64。修复后的原生运行结果另以远端 CI 为准。
- 目标包 CI：L0、知识图谱、PR 杂项、L1、破坏性负测、补丁安全与包内容门禁
  全部通过；当前分支还包含 #44413 所需
  的共享预下载器修复，合入前需按 W2 与软件包 PR 分离。
- 仓库回归：9/11 套件通过，与实现前基线一致；`test_v1220.py` 的 CI 专用
  Git 路径和 `test_v1221.py` 的基线 catalog 缺项仍是仅有两项失败。
- 通用 `finish` 已实际执行；其旧式原始 tar/预编译 packaging 假设及仓库已有
  知识条目问题被如实记录，未伪造门禁标记。

本地 x86_64 虚拟机是不可调试的 production 镜像。HDC shell 处于 SELinux enforcing 的
`u:r:sh:s0`；最小探针确认 `socket(AF_INET)` 成功，但 `bind(127.0.0.1, 0)`
返回 `EACCES`，且 HDC `smode` 被镜像拒绝。因此设备上的网络 server/client
回环不能在 shell 身份执行；这项运行时能力已由 Linux 原生上游套件和消费者
覆盖，HarmonyOS 端没有通过跳过失败或伪造标记来宣称网络回环通过。

完整证据见 `reports/test-report.md`。
---

**编译结束**: 2026-09-11 14:42
**最终状态**: built
