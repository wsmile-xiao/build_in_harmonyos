## PR 信息
- **三方库名称**：foonathan-memory
- **上游版本**：0.7
- **上游仓库地址**：https://github.com/foonathan/memory
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E267、E140、E321（draft）；记录见版本级 `manifest.yaml`、`notes.md` 和 `knowledge/drafts/E321-draft-333C.{kv,md}`。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 39 | Catch2 上游 `test/`，CTest 注册 1 个测试 |
| 集成测试 | 0 | 上游未单独注册集成测试 |
| 其他测试 | 0 | 无 |
| **合计** | **39** | 39 个 Catch2 test cases，140870 assertions |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 39 | 不变 | 上游 Catch2 测试全部通过 |
| 集成测试 | 0 | 不变 | 无 |
| 鸿蒙特有测试 | 1 | 新增 | Conan `test_package` 调用三种 allocator、memory_pool 和 std_allocator |
| **合计** | **40** | +1 | 含 39 个上游用例和 1 个消费者测试 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

补丁仅修改上游构建平台检测和 POSIX hosted allocator 实现，没有改动上游测试文件；Windows 保留原生分配路径。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，补充了 Conan 消费者测试以验证 OHOS 安装包和公共 API
- [ ] **否**，上游已有测试用例覆盖

- **补全的测试范围**：新增 1 个 Conan `test_package` 测试程序，覆盖 `heap_allocator`、`malloc_allocator`、`new_allocator` 的 max alignment 和 zero-size 分配，以及 `memory_pool`/`std_allocator` 的 `std::vector` 使用。
- **补全原因**：上游测试验证库内部行为；消费者测试验证 Conan target、头文件、静态库链接和 HarmonyOS POSIX 运行时分配行为。
- **新增测试文件清单**：
  1. `archives/f/foonathan-memory/0.7/test_package/test.cpp` — Conan 消费者功能与对齐测试。
  2. `archives/f/foonathan-memory/0.7/test_package/CMakeLists.txt` — CMake 查找并链接 `foonathan_memory` target。

## 适配内容

- `0001`：让安装目录识别 `OHOS`、`HarmonyOS` 和 `OpenHarmony`。
- `0002`、`0004`、`0005`：POSIX hosted 路径使用 `posix_memalign`，覆盖默认、malloc 和 new allocator，并将零字节请求提升为 1 字节后释放；Windows 保留原生分配路径。
- `0003`：原生 HarmonyOS host/target 允许生成 `nodesize_dbg` 所需的节点大小头文件。
- Conan 配方默认静态库，提供 `with_tools`，导出 `foonathan_memory` CMake 文件名和 target。

## 验证结果

- 编译状态：通过（OHOS Conan profile，clang 15.0.4，CMake 4.1.2，Conan 2.29.1）。
- 上游测试用例通过率：39/39（100%），140870 assertions 全部通过。
- 新增测试用例通过率：1/1（100%）。
- Conan 验证：G1/G2/G3/G4/L2/L4/L5 PASS；本地 W3 CI 定向 rebuild 通过。

## 验证命令

```bash
PROFILE=/storage/Users/currentUser/ws/foonathan-memory-0.7/ci/conan/profiles/ohos-aarch64
conan create archives/f/foonathan-memory/0.7 \
  -pr:h="$PROFILE" -pr:b="$PROFILE"
zsh ci/conan/build_and_test.sh archives/f/foonathan-memory/0.7
```

## 补充说明

- `finish` 的通用 G0 clean verifier 对 CMake-only 工程仍无条件执行 `./configure`，因此该旧步骤 exit 127；实际 Conan W3、上游 CTest、消费者测试和 Conan verify 均通过。未修改框架文件。
- 本地 W3 预下载会临时改写 `conandata.yml` 为 `file://` 缓存路径；提交前已恢复为官方 HTTPS URL及固定 SHA-256。
- 远端 `ohpcd` 查询受 `system acceleration policy not enabled` 限制，未宣称 registry 已发布。
