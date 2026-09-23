# nuraft 3.0.0 适配笔记

## 编译环境
- 构建系统: cmake (cmake_minimum_required 3.26)
- 编译日期: 2026-09-12
- 编译器: clang 15.0.4 (target aarch64-unknown-linux-ohos)
- 交叉 profile: ci/conan/profiles/ohos-aarch64 (os=OHOS, arch=armv8, cppstd=17)
- 状态: built

## 适配策略

采用**非 WITH_CONAN 模式 + vendored ASIO + DISABLE_SSL** 的最简路径：

1. **vendored ASIO**：上游 prepare.sh 的 manifest.sh 指定 `ASIO_RELEASE="asio-1-24-0"`，
   源码包本身不含 asio。conandata.yml 双 sources（nuraft v3.0.0 + asio-1-24-0），
   source() 中把 asio 仓库的 `asio/` 子树移到源码根 `asio/`，CMake 的
   `find_path(ASIO_INCLUDE_DIR HINTS ${PROJECT_SOURCE_DIR}/asio/asio/include)` 直接命中。
   少一个外部依赖（ohpcd 制品仓无 asio 配方）。
2. **DISABLE_SSL=1**：`src/asio_service.cxx` 中 `SSL_LIBRARY_NOT_FOUND` 宏触发
   9 处 `#ifdef` 条件编译，SSL 相关代码（asio::ssl::stream / SSL_CTX 等）整体排除，
   无需 openssl 依赖。
3. **BUILD_EXAMPLES=OFF**：examples 不编进产物（quick_start/calculator/echo）。
4. **BUILD_TESTING**：由配方选项 `build_tests` 控制，默认 OFF（CI 快速稳定）；
   上游测试计数在本地单独实测（见下）。

## 编译步骤

```bash
conan create archives/n/nuraft/3.0.0 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing
```

手工等价（探针验证）：
```bash
cmake -G Ninja -DCMAKE_SYSTEM_NAME=HarmonyOS -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_STANDARD=17 -DCMAKE_BUILD_TYPE=Release \
  -DDISABLE_SSL=1 -DBUILD_EXAMPLES=OFF -DBUILD_TESTING=ON
ninja static_lib shared_lib
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时 | 本机网络无法直连 github.com web | 改用 codeload.github.com 下载官方 tarball 计算 sha256；conandata.yml 仍写官方 github archive URL（CI 有镜像 fallback），sha256 与 Homebrew homebrew-core 双源核对一致 |
| 2 | 公共头文件是否依赖 asio.hpp | consumers 编译需确认 | asio_service.hxx 用 pimpl（asio_service_impl* fwd decl）隐藏 asio.hpp，实测消费者程序仅需 `-I include` + `-lnuraft -ldl -lz -pthread`，无需 asio 头文件 |

## 源码修改

无需补丁：核心库（26 个 .cxx）、上游测试（10 个测试目标）、消费者冒烟程序
探针均一次编译通过，仅 2 个无害 unused-variable warning。

## 依赖版本

- vendored ASIO: asio-1-24-0（standalone，仅库内部使用）
- 系统库: dl / z / pthread（OHOS 内置）
- 无 conan 外部依赖（W0 已确认 ohpcd 制品仓无 nuraft/asio 配方）

## 验证结果

### 上游测试（HOS aarch64 本地实测，真实工具链）

| 测试 | 结果 | 耗时 |
|------|------|------|
| raft_server_test | PASS | 16.78s |
| new_joiner_test | PASS | 1.07s |
| failure_test | PASS | 2.24s |
| asio_service_stream_test | PASS | 9.93s |
| buffer_test | PASS | 0.03s |
| serialization_test | PASS | 0.06s |
| timer_test | PASS | 1.28s |
| strfmt_test | PASS | 0.03s |
| stat_mgr_test | PASS | 0.03s |
| logger_test | PASS | 0.12s |

- 上游 CMakeLists 显式 SKIP：asio_service_test（"takes too long"）、stream_functional_test（"test fails"）
- raft_bench 为 benchmark 非测试用例（Not Run 不计入）
- 合计 **10/10 通过**（100%）

### test_package（消费者冒烟）

3 节点 in-memory Raft 集群（asio 回环 127.0.0.1），单进程内验证：
- 3 节点初始化 + 节点 1 单节点选举为 leader
- add_srv 扩展集群至 3 节点，集群保持 leader
- leader append 一条日志，全部节点 commit index 前进（实测 3/3 节点 committed=3）
- **12/12 断言通过**

## 注意事项

1. 静态库消费者链接需 `-ldl -lz -pthread`（cpp_info.system_libs 已声明）
2. 上游 CMake 强制同时构建 shared/static，静态模式 package 后删除 .so
3. noexec 限制：CI worker 若限制回环网络/线程，test_package 冒烟与上游网络相关测试
   可能受影响，如实按 CI 结果说明
4. SSL 功能被禁用（DISABLE_SSL）：如需 SSL 需引入 openssl 依赖并重新适配
