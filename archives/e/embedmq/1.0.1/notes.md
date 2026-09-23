# embedmq 1.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 上游测试双口径台账（源码声明 / 配置可执行 / 实际执行）

### 源码声明枚举（可复制枚举规则：tests/ 下用户测试源中独立用例函数）

| # | 测试源 | 独立用例（函数名） | 分类理由 |
|---|--------|--------------------|----------|
| 1 | tests/test_embedmq.c | test_uuid_deterministic | 用户测试源独立 TEST 函数（main 直接调用） |
| 2 | tests/test_embedmq.c | test_create_destroy | 同上 |
| 3 | tests/test_embedmq.c | test_register_and_post | 同上 |
| 4 | tests/test_embedmq.c | test_payload_received | 同上 |
| 5 | tests/test_embedmq.c | test_post_id_hot_path | 同上 |
| 6 | tests/test_embedmq.c | test_static_mode | 同上 |
| 7 | tests/test_embedmq.c | test_queue_full | 同上 |
| 8 | tests/test_embedmq.c | test_handler_table_full | 同上 |
| 9 | tests/test_embedmq.c | test_post_exceeds_max_msg_size | 同上 |
| 10 | tests/test_embedmq.c | test_concurrent_producers | 同上 |
| 11 | tests/test_embedmq_cpp.cpp | test_subscribe_and_publish | 用户测试源独立 TEST 函数（C++ main 直接调用） |
| 12 | tests/test_embedmq_cpp.cpp | test_lambda_capture | 同上 |
| 13 | tests/test_embedmq_cpp.cpp | test_publish_id_hot_path | 同上 |
| 14 | tests/test_embedmq_cpp.cpp | test_raii_destroy | 同上 |
| 15 | tests/test_embedmq_cpp.cpp | test_move | 同上 |
| 16 | tests/test_embedmq_cpp.cpp | test_multi_subscribe_no_uaf | 同上 |

### 非独立用例（不计入上游用例，列入台账备查）

| 条目 | 类型 | 是否独立上游用例 | 理由 |
|------|------|------------------|------|
| examples/basic.c | 样例 | 否 | 示例程序，非测试断言用例 |
| examples/basic_cpp.cpp | 样例 | 否 | 示例程序 |
| examples/benchmark.c | 基准 | 否 | 性能基准，非断言用例 |
| sim/freertos/main.c + FreeRTOSConfig.h | 仿真器 | 否 | FreeRTOS POSIX 仿真（默认 OFF，需 -DEMBEDMQ_BUILD_FREERTOS_SIM=ON 且拉取 FreeRTOS kernel） |
| include/embedmq.h / embedmq.hpp | 框架头文件 | 否 | 库公开头文件，非测试 |
| pal/* | PAL 平台层 | 否 | 平台抽象实现，非测试 |
| src/* | 库源码 | 否 | 被测对象本身 |

### 映射（源码声明 → 构建目标 → ctest 注册项 → 实际执行）

| 源码声明（16 项） | 预处理/构建条件 | 构建目标 | ctest -N 注册项 | 实际执行 |
|-------------------|----------------|----------|-----------------|----------|
| 1-10 (test_embedmq.c) | EMBEDMQ_BUILD_TESTS=ON（默认 ON），无互斥分支 | test_embedmq | embedmq_tests | 通过（10/10） |
| 11-16 (test_embedmq_cpp.cpp) | EMBEDMQ_BUILD_TESTS=ON（默认 ON），无互斥分支 | test_embedmq_cpp | embedmq_cpp_tests | 通过（6/6） |

### 双口径统计

- source_declared_total: 16（tests/ 用户测试源独立用例）
- configured_executable_total: 2（test_embedmq、test_embedmq_cpp）
- executed_passed_total: 16
- 失败数: 0
- 未运行/未实例化数: 0
- 全量通过率: 16/16 = 100%（通过数/全量发现数）
- 当前配置可执行集合通过率: 16/16 = 100%

### 实际执行证据（OHOS 交叉工具链 clang 15 aarch64-linux-ohos）

```bash
$ cmake -S . -B build-native -DEMBEDMQ_BUILD_TESTS=ON -DEMBEDMQ_BUILD_EXAMPLES=ON \
    -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
$ cmake --build build-native -j4   # 100% 成功
$ ctest --output-on-failure        # 2/2 Passed
$ ./test_embedmq       # 10 个 [PASS]：uuid/create_destroy/register_and_post/payload_received/post_id_hot_path/static_mode/queue_full/handler_table_full/post_exceeds_max_msg_size/concurrent_producers
$ ./test_embedmq_cpp    # 6 个 [PASS]：subscribe_and_publish/lambda_capture/publish_id_hot_path/raii_destroy/move/multi_subscribe_no_uaf
```

## 编译步骤

1. init-build：tarball 下载核验（SHA-256 2f4526b8bae7fb318dadb9f60a3b0695bf346f2e8092ce97bf9ec1f02a4554d0，官方 GitHub tag v1.0.1，commit b8e9601305936e45cf36f3d1e9d257b4ec5d6f17）
2. lang-preflight：task=cpp, detected=cpp 匹配通过
3. CMake 配置：`cmake -S . -B build-native -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++`（PAL=linux 默认，静态库）
4. 编译：`cmake --build build-native -j4` → 100%
5. 测试：`ctest --output-on-failure` → 2/2 Passed

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时 | 本机到 github.com 直连网络不可达 | 使用 CI 同款 gh-proxy.com 镜像下载官方 tarball，SHA-256 与官方一致；conandata.yml 仍保留官方 HTTPS URL（R39），CI 自动加镜像 fallback |
| 2 | /tmp 只读 | E002 已知平台陷阱（HMDFS） | 使用 $TMPDIR=$HOME/tmp（默认已配置） |

## 源码修改

无（零补丁适配；上游 CMake 工程无平台宏依赖，PAL linux 后端 pthread+POSIX sem 在 OHOS 可用）

## 依赖版本

- 无外部依赖（零依赖库，仅链接 pthread）
- 工具链：clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)

## 验证结果

```bash
ctest --output-on-failure
100% tests passed, 0 tests failed out of 2
```

## 注意事项

- embedmq 为纯 C/C++ 零依赖消息分发库，CMake 构建，PAL 层可选 linux/freertos/none；默认 linux PAL 仅用 pthread + POSIX semaphore，OHOS 可直接使用。
- 无 CLI 产物（纯静态库），不需要 commands.json。
---

**编译结束**: 2026-09-22 00:45
**最终状态**: built

## 知识候选台账与七轴查重（知识库扩展评估）

### 候选 C1：Conan 2 配方手动打包（上游 CMakeLists 无 install() 规则）

- 真实错误（实际日志）：
  1. conan create 包内空——`package(): WARN: No files in this package!`，test_package 阶段
     `CMake Error ... cmakedeps_macros.cmake:81: Library 'embedmq' not found in package`。
  2. 初版改用 `self.copy(...)` 报 `AttributeError: 'EmbedmqConan' object has no attribute 'copy'`。
  3. 修正为 `copy(self, pattern, src, dst)`（conan.tools.files）后，`dst="include"` 且 `src="include"`
     报 `copy() 'src' and 'dst' arguments must have different values`；dst 必须用
     `os.path.join(self.package_folder, ...)` 绝对路径。
- 根因：上游 CMakeLists 只 build 不 install；Conan 2 中 `self.copy` 已移除，须用
  `conan.tools.files.copy`；成对目录（src==dst 同名字面量）被 API 拒绝，dst 须以 package_folder 为根。
- 修复：package() 中 `copy(self, "libembedmq.a", dst=os.path.join(self.package_folder,"lib"),
  src=self.build_folder, keep_path=False)` + 头文件同理指向 source_folder/include；随后
  `rm -rf` 缓存中陈旧空包后 conan-verify 全过（G0-G4 + L2/L4/L5）。
- 验证：conan-verify 全部门禁 PASS；test_package 2/2 通过（含 test_ohos 鸿蒙专项）。
- 适用范围：所有"上游 CMake 工程无 install() 规则"的 Conan 2 库配方。
- 四范围查重：正式 knowledge/graph 索引未命中（E217 为"头文件装到 include/<subdir>"，根因不同）；
  草稿层 search 无同 stem 配对；图谱引擎命 E392（raw-makefile 配方模式，方向不同），无遮挡。

### 候选 C2：test_package 测试代码用 assert 做前置检查在 NDEBUG 下静默失效（Release 空转/UB）

- 真实错误（实际日志）：初次 test_ohos.c 用 `assert(q != NULL)`、`assert(pthread_create(...) == 0)`
  做前置检查。OHOS 工具链手工编译 `-O2`（无 NDEBUG）正常通过 delivered=1000；但以 Conan Release
  `-DNDEBUG` 构建后稳定 `Signal 11 (core dumped)`（-O2/-O3 均复现）；ASAN 构建下
  `delivered=0` 却"PASS"（断言被编译为空→假通过）。
- 根因：C11 assert() 在 NDEBUG 下展开为空；测试把"关键前置条件"寄托在 assert 上，
  Release 构建下前置检查消失 → 空指针/未初始化 join 句柄 → 崩溃或静默假通过。
- 修复：全部前置检查改为显式错误码 + `fprintf(stderr,...); return 2;`，只保留纯后置断言输出
  （PASS/FAIL 以退出码为准）；重写后 NDEBUG 构建 5/5 通过、conan test_package 2/2 通过。
- 验证：`-fPIC -O2 -O3 -DNDEBUG`（与 CI flags.make 一致）下连续 5 次 exit 0；conan create 内
  test_ohos Passed。
- 适用范围：任何在 test_package/消费者用例中用 assert 承载控制流的配方（跨 CMake/Conan 通用）。
- 四范围查重：正式 E259 命中（"assert 副作用被 NDEBUG 编译掉"）——触发域部分重叠（NDEBUG×assert），
  但 E259 聚焦"上游源码 assert(含副作用表达式)"的 latent bug；本候选聚焦"测试代码用 assert 做
  前置检查 → Release 空转/崩溃"的测试构造边界，方案（显式错误码替代 assert 控制流）不同，属于新增差异。

### 候选 C3：GitHub 直连超时 → gh-proxy 镜像下载并核验 SHA-256（既有知识复用）

- 现象：直接 curl github.com 超时（无代理直连不可达）；经 `https://gh-proxy.com/<官方URL>` 下载
  v1.0.1 tarball 成功，SHA-256 2f4526b8... 与 CI 镜像注入后一致；conandata.yml 保留官方 URL（R39）。
- 查重：E017（github URL 镜像注入）与 E415（CI 改写 conandata 后恢复）已覆盖，属既有知识复用，
  非新增；不存在需要新草稿的差异。

### 七轴查重

| 轴 | C1 | C2 | C3 |
|----|----|----|----|
| exact_duplicate | false（E217 根因不同） | false（E259 面向源码副作用） | true→复用 E017/E415 |
| causal_duplicate | false | false（测试构造边界不同） | true |
| trigger_overlap | 部分（conan create 阶段） | 部分（NDEBUG×assert） | 相同 |
| solution_overlap | 低（E217 为 includedirs 修正） | 低（E259 为 hoist 副作用） | 相同 |
| combination_novelty | true（无 install+Conan2 copy API 组合未见） | true（断言控制流×Release 崩溃组合） | false |
| boundary_novelty | true（package_folder 绝对 dst 约束） | true（测试代码侧 NDEBUG 失效边界） | false |
| test_migration_novelty | true | true | false |

### 路径判定

- C3：已有条目完整复用 → 不计入新增。
- C1、C2：均"已验证 + 可跨库复用 + 查重未命中/部分覆盖且存在新增差异"→ **必须走路径 B（new_draft）**，
  建立同 stem 的 .md/.kv 草稿，随本库 PR 一并交付（不另建脱离三方库的知识库 PR）。
- 决定：**new_draft**（C1 + C2 两个草稿配对）。
