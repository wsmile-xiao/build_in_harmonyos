- **三方库名称**：robin-hood-hashing
- **上游版本**：3.11.5
- **上游仓库地址**：https://github.com/martinus/robin-hood-hashing
- **适配路径**：路径 B（贡献创新 / 知识库扩展）
- **使用知识库**：DRAFT-robin-hood-hashing-3.11.5-clang15-has-trivial-copy-deprecated（本次新增草稿，待 promote）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 127 | 来源：src/test/unit/*.cpp（doctest 2.4.6 驱动，单一 rh 可执行） |
| 集成测试 | 0 | 无独立集成测试 |
| 其他测试 | 73 | 性能 bench/count/fuzz 类用例（doctest 默认跳过，未运行） |
| **合计** | **127** | 实际运行的 doctest test cases |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 127 | 不变 | 上游全部 test cases 在 OHOS arm64 实跑 |
| 集成测试 | 0 | 不变 | - |
| 鸿蒙特有测试 | 1 | 新增 | test_package 消费者测试（conan create 内运行） |
| **合计** | **128** | **+1** | 127 上游 + 1 消费者验证 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游测试程序（rh，doctest 驱动）原样编译运行，未改动任何测试源码。
> 仅测试程序编译参数层面：禁用 clang-tidy（上游 CMake 在 Clang 下自动启用
> `CMAKE_CXX_CLANG_TIDY`，其风格检查误伤测试代码）并关闭
> `-Wsign-conversion`（OHOS sysroot `PERF_EVENT_IOC_ID` 宏触发）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 说明：本库为 header-only，上游无独立测试入口（测试全部挂在
> src/test/unit 的 doctest 可执行内）。为满足 R34 消费者实质验证，
> test_package 新增 1 个消费者测试：
> - **补全的测试范围**：实际 include `robin_hood.h` 并验证
>   `robin_hood::unordered_map`（emplace/find/erase）与
>   `robin_hood::unordered_set`（insert/count）核心 API。
> - **新增测试文件清单**：
>   1. `test_package/test.cpp` — 消费者 API 验证（assert 判定，非空壳）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：127/127（100%）（2,164,686 assertions 全部通过，0 failed）
- 新增测试用例通过率：1/1（100%）（conan create test_package）

## 补充说明

- **适配类型**：header-only C++14 哈希表库（robin_hood hash map/set），
  零运行时依赖，无编译步骤；conanfile.py 仅安装头文件。
- **补丁 0001**：clang 15+ 弃用 `__has_trivial_copy`。clang 预定义
  `__GNUC__=4`，会误入上游 `#if defined(__GNUC__) && __GNUC__ < 5` 兼容分支，
  配合 `-Werror,-Wdeprecated-builtins` 编译失败。补丁排除 clang
  （`!defined(__clang__)`），改用 `std::is_trivially_copyable`。
- **知识草稿**：clang15 `__has_trivial_copy` 弃用为可跨库复用的编译模式，
  已创建 `knowledge/drafts/DRAFT-robin-hood-hashing-3.11.5-clang15-has-trivial-copy-deprecated.{kv,md}`
  与三方库归档同 PR 提交，待主编 promote。
- 上游测试 73 skipped 为性能 bench/count 类用例（doctest 默认跳过），
  不参与断言，不影响功能正确性结论。
