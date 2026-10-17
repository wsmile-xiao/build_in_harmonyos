- **三方库名称**：swift-corelibs-blocksruntime
- **上游版本**：6.3.3（源码标签 `swift-6.3.3-RELEASE`）
- **上游仓库地址**：https://github.com/swiftlang/swift-corelibs-blocksruntime
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

已检查官方 `swift-6.3.3-RELEASE` 源码包完整文件树、根目录 `CMakeLists.txt` 和 `src/BlocksRuntime/CMakeLists.txt`。上游仅包含构建文件、运行时源码、头文件、module map、CMake 配置模板、README 和 LICENSE，不存在测试目录、CTest 注册或测试目标。

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游源码无测试目录或测试目标 |
| 集成测试 | 0 | 上游源码无集成测试 |
| 其他测试 | 0 | 上游源码无其他测试 |
| **合计** | **0** | **全部上游用例已核查，无可执行用例** |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有消费者测试 | 7 | +7 | 7 个独立可执行程序，逐项验证 BlocksRuntime 核心 ABI 与生命周期语义 |
| **合计** | **7** | **+7** | **7/7（100%）通过** |

新增测试明细：

| 测试可执行项 | 验证范围 | 结果 |
|---|---|---|
| `test_global_block` | 无捕获全局 Block 的复制、调用与释放 | PASS |
| `test_captured_block` | 捕获值栈 Block 复制到堆并校验调用结果 | PASS |
| `test_escape_lifetime` | Block 离开定义栈帧后仍可安全调用 | PASS |
| `test_byref_capture` | `__block` 可变捕获的 forwarding 与多次修改 | PASS |
| `test_nested_block` | 捕获另一个 Block 的嵌套 Block 复制与调用 | PASS |
| `test_retain_release` | 堆 Block 重复复制、释放一个引用后继续调用 | PASS |
| `test_block_metadata` | `Block_size`、签名标志和栈/堆元数据一致性 | PASS |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

上游本身没有测试用例，且本适配未修改任何上游源码。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：新增 7 个独立测试程序和 7 个结果断言，覆盖全局 Block、捕获值 Block、离栈生命周期、`__block` forwarding、嵌套 Block、重复复制/引用释放及 ABI 元数据查询。
- **补全原因**：上游 6.3.3 源码仅提供运行时实现和构建配置，没有正式测试框架或测试目标。
- **新增测试文件清单**：
  1. `test_package/test_global_block.c`
  2. `test_package/test_captured_block.c`
  3. `test_package/test_escape_lifetime.c`
  4. `test_package/test_byref_capture.c`
  5. `test_package/test_nested_block.c`
  6. `test_package/test_retain_release.c`
  7. `test_package/test.c`（ABI 元数据测试）

每个源文件构建为独立可执行项，Conan `test()` 逐项运行；任意一项失败都会使 `conan create` 返回失败。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：`0/0（N/A，上游无测试用例）`
- 新增测试用例通过率：`7/7（100%）`
- 新增测试断言：7 个，全部通过
- 验证环境：HarmonyOS PC arm64，Clang 15.0.4，Conan 2.29.1

```bash
conan create archives/s/swift-corelibs-blocksruntime/6.3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=swift-corelibs-blocksruntime/*
```

实际运行输出：

```text
global_block: PASS
captured_block: PASS
escape_lifetime: PASS
byref_capture: PASS
nested_block: PASS
retain_release: PASS
block_metadata: PASS
```

## 补充说明

- 上游通过率采用 `0/0（N/A）`，不写作 100%，避免在无上游测试时产生误导。
- 官方源码无需补丁即可在 HarmonyOS PC arm64 上构建。
- 测试直接链接 Conan 包导出的 `BlocksRuntime::BlocksRuntime`，验证下游真实消费链路，而非仅测试源码内部函数。
