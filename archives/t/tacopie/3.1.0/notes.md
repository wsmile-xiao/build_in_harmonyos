# tacopie 3.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-17
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. 官方源码: https://github.com/Cylix/tacopie (tag 3.1.0 tarball, sha256 6072fdd9…f050ce)
2. Conan 配方（共享库）:
   ```bash
   conan create . --profile=ohos-aarch64 --build=missing
   ```
   配方: BUILD_SHARED_LIBS=ON, BUILD_TESTS=OFF, BUILD_EXAMPLES=OFF,
   CMAKE_POLICY_VERSION_MINIMUM=3.5（上游 cmake_minimum_required 2.8.7 vs CMake 4.x）。
3. 配方构建 + test_package 端到端通过（2/2 用例，0 failed）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任何带超时的 `tcp_client::connect()` 都抛 `connect() timed out`（即使服务端已 accept） | 上游 `unix_tcp_socket.cpp` connect() 的 `select(0, NULL, &set, NULL, &tv)` 把 nfds 写成 0，内核不监视任何 fd，select 必然等满超时返回 0 → 永远判超时 | 补丁 0001: `select(m_fd + 1, …)`（+1/-1） |
| 2 | test_package 消费者测试中服务端 `async_read` 回调从不触发 | 连接回调返回 true 时 tcp_server 不持有客户端；read 回调用 `[&]` 引用捕获时 shared_ptr 不被持住，连接回调返回后 tcp_client 被析构、套接字关闭 | 测试中按值捕获 `[client, …]`（与上游示例 std::bind 同模式） |
| 3 | CMake 4.x 报 "Compatibility with CMake < 3.5 has been removed" | 上游 `cmake_minimum_required(2.8.7)` 被 CMake 4.x 拒绝 | conanfile generate() 设置 cache_variables `CMAKE_POLICY_VERSION_MINIMUM=3.5` |

## 源码修改

- `patches/0001-fix-connect-select-nfds.patch`：unix connect() 的 select() nfds 0 → m_fd+1。

## 上游测试台账（官方 3.1.0 tag 源码全量枚举）

**结论：官方 3.1.0 tag 未携带任何独立上游测试用例。**

枚举清单（按可复制枚举规则逐项核实，grep -rnE 'TEST_CASE|TEST(_F|_P|_T)?\\(' 覆盖 includes/ sources/ tests/ examples/，仅命中 main.cpp 的 RUN_ALL_TESTS 调用）：

| 入口 | 分类 | 是否独立上游用例 | 是否实际运行 | 结果/原因 |
|---|---|---|---|---|
| tests/sources/main.cpp | 用户测试源（gtest runner 主函数） | 否（0 个 TEST_CASE 声明） | 是 | 用 ohpcd gtest/1.17.0 实际编译链接运行：`Running 0 tests from 0 test suites … PASSED 0 tests`（runner 本身在 OHOS 工具链编译运行正常） |
| tests/CMakeLists.txt | 测试构建目标声明（tacopie_tests，glob sources/spec，链接 gtest） | 否（框架注册清单，无用例可实例化） | 是 | tag 内无 spec/*.cpp 可 glob；配方 BUILD_TESTS=OFF（上游测试依赖 ExternalProject git clone googletest） |
| tests/sources/spec/** | 上游 spec 用例目录 | 不存在（tag 未包含） | 否 | 官方 3.1.0 tag 不携带（tarball 全量列出无此目录） |
| examples/logger.cpp, tcp_client.cpp, tcp_server.cpp | 样例 | 否（非测试） | 否 | 样例，不进入测试计数 |
| docs/, msvc15/, assets/, .doxygen | 文档/工程/素材 | 否 | 否 | 非测试 |

双口径统计：
- `source_declared_total` = 0（官方 tag 源码中独立 TEST_CASE 声明总数，实测 grep 全仓 0 命中）
- `configured_executable_total` = 0（当前 OHOS 配置可实例化/注册的独立可执行用例数；上游 runner 链接后 0 tests from 0 suites）
- `executed_passed_total` = 0，失败 0，未实例化 0
- 全量通过率：0/0 不适用（声明数为 0，如实说明 tag 无独立用例，不以 0/0=100% 或 0/1 充数）
- 映射：源码声明（0 个 TEST_CASE）→ 构建目标（tacopie_tests，无 spec 源可 glob）→ ctest -N/GTest 注册项（0）→ 实际执行日志（gtest runner 0 tests, PASSED）

gtest registry 复查：`conan download gtest/1.17.0 -r=ohpcd --only-recipe` 两次（首跳 2026-09-17T13:04Z 成功；最终回报前复查成功），gtest/1.17.0 与 gmock/1.17.0 均已在 ohpcd 发布。上游 runner 已用该 gtest 实际运行，无依赖缺失。

## 依赖版本

- 构建期：无第三方依赖（库本体仅 C++11 + pthread）。
- 测试期：googletest/gmock 1.17.0（ohpcd registry 已发布；仅用于上游 runner 实例化验证，配方 BUILD_TESTS=OFF）。

## 消费者用例（test_package，2 个，均通过）

1. `test_tacopie`：真实 TCP 回环往返。tcp_server::start → tcp_client::connect（固定补丁后 3000ms 超时路径）→ async_write → 服务端 async_read 校验 payload 一致。验证公开 API：start/stop/is_running/connect/is_connected/async_read/async_write/disconnect。
2. `test_tacopie_hmos`：OHOS 专项。tcp_server 绑定 + is_running + loopback connect/async_read/async_write + disconnect/stop 清理路径。

## 知识候选台账与七轴查重（Path B 判定）

候选 1（C1）：tacopie unix connect() 超时路径 select() nfds=0 → 任何带超时 connect 必抛 timed out
- 真实错误：`connect() timed out`（服务端已 accept）；修复：nfds 0 → m_fd+1（补丁 0001，+1/-1）
- 根因：POSIX select() nfds 语义错误（内核不监视任何 fd），与平台无关、OHOS 适配首现
- 验证：补丁前后对照诊断（python 服务端 accept 成功仍超时 → 修复后 ok=1）；conan create 2/2 用例通过
- 适用范围：任何以非阻塞 connect + select 等待可写的 C/C++ TCP 库（tacopie 及同类 select 驱动库）
- 四范围查重：正式知识（index.tsv/doc 全量 grep select/nfds/connect/timed out → 未命中）、
  图谱（graph/*.kv → 未命中）、草稿（drafts/*.kv → 未命中）、既有归档 notes（cpplocate 等 → 未命中）

七轴查重（C1）：
- exact_duplicate: false（无既有条目）
- causal_duplicate: false（E086 SO_PEERCRED、E008/E076 socket EACCES 均不同根因）
- trigger_overlap: false（"connect() timed out" 无既有条目覆盖；E017 是下载超时非 socket connect）
- solution_overlap: false（既有条目无 select nfds 修复方案）
- combination_novelty: true（select nfds=0 语义错误修复，跨库可复用，OHOS 生态首见）
- boundary_novelty: true（适用边界明确：select 驱动 TCP 库的非阻塞 connect；不适用于 epoll 驱动库）
- test_migration_novelty: false（无上游测试迁移内容）

候选 2（C2）：tcp_server 连接回调返回 true 时 server 不持有客户端，异步回调须按值捕获 client shared_ptr
- 真实错误：消费者测试服务端 async_read 回调从不触发（new_client_seen=1 但 read 不回调）
- 根因：tacopie 连接回调语义（返回 true = 客户端由调用方持有）；`[&]` 引用捕获不持住 shared_ptr，
  回调返回后 tcp_client 析构、socket 关闭
- 验证：按值捕获 `[client, ...]` 后 read 回调触发、payload 一致（diag_t5 ok=1；conan create 通过）
- 适用范围：tacopie tcp_server 消费者（测试/业务代码）
- 四范围查重：未命中任何既有条目（含 E086 等 socket 类）
- 七轴：exact/causal/trigger/solution_overlap 均 false；combination_novelty: true；
  boundary_novelty: true（tacopie 特有 API 语义）；test_migration_novelty: false

候选 3（C3）：CMake 4.x 移除 <3.5 兼容 → 上游 cmake_minimum_required 2.8.7 配置失败
- 四范围查重：**命中既有正式知识 E103**（bump-cmake-minimum-version，error_signature 精确匹配
  "Compatibility with CMake.*3\.5 has been removed"），solution_overlap: true
- 差异：E103 推荐改 CMakeLists.txt cmake_minimum_required；本轮采用 conanfile
  `CMAKE_POLICY_VERSION_MINIMUM=3.5` cache_variables 免补丁方案（与 cpplocate 2.3.0 同模式）
- 判定：复用 E103，不新建草稿；C3 作为既有知识覆盖记录，不计入新增

关系字段：C1 similar_to [E086, E008]；C2 caused_by [tacopie tcp_server API 语义（库设计）]；
C3 prerequisite_of [E103（已存在）]

路径判定：**Path B（知识库扩展）成立**——C1、C2 均经验证、可跨库/跨消费者复用、查重未命中，
按同 stem 规则建立 E543 草稿对（knowledge/drafts/E543-draft-DE47.kv + .md），
C3 复用 E103 不计新增。标题前缀：【知识库扩展】。
---

**编译结束**: 2026-09-17 21:20
**最终状态**: built
