# swift-corelibs-blocksruntime 6.3.3 测试报告

**测试日期**：2026-08-22
**测试平台**：HarmonyOS PC arm64（`os=OHOS`，`arch=armv8`）
**编译器**：Clang 15.0.4
**构建系统**：CMake + Conan 2.29.1

## 上游全部测试核查

已检查官方 `swift-6.3.3-RELEASE` 源码包的完整文件树、根目录 `CMakeLists.txt` 和 `src/BlocksRuntime/CMakeLists.txt`。源码包仅包含构建文件、运行时源码、头文件、module map、CMake 配置模板、README 和 LICENSE；不存在 `test/`、`tests/`、CTest 注册、测试可执行目标或其他上游测试套件。

| 测试类型 | 上游用例数 | 执行结果 |
|---|---:|---|
| 单元测试 | 0 | 无可执行上游用例 |
| 集成测试 | 0 | 无可执行上游用例 |
| 其他测试 | 0 | 无可执行上游用例 |
| **合计** | **0** | **0/0（N/A，上游无测试）** |

> 上游通过率不写作 100%，因为上游没有任何测试用例；以 `0/0（N/A）` 如实记录。

## 补全的消费者测试

由于上游无测试套件，适配在 `test_package/` 中新增 7 个相互独立的真实消费者测试。每个用例编译为单独的可执行文件，由 Conan `test()` 逐项运行；任意用例返回非零都会使 `conan create` 失败。

| 编号 | 测试可执行项 | 验证范围 | 结果 |
|---:|---|---|---|
| 1 | `test_global_block` | 无捕获全局 Block 的复制、调用与释放 | PASS |
| 2 | `test_captured_block` | 捕获值栈 Block 复制到堆并校验调用结果 | PASS |
| 3 | `test_escape_lifetime` | Block 离开定义栈帧后仍可安全调用 | PASS |
| 4 | `test_byref_capture` | `__block` 可变捕获的 forwarding 与多次修改 | PASS |
| 5 | `test_nested_block` | 捕获另一个 Block 的嵌套 Block 复制与调用 | PASS |
| 6 | `test_retain_release` | 堆 Block 重复复制、释放一个引用后继续调用 | PASS |
| 7 | `test_block_metadata` | `Block_size`、签名标志和栈/堆元数据一致性 | PASS |
| **合计** | **7 个独立用例** | **7 个结果断言** | **7/7（100%）** |

实际输出：

```text
global_block: PASS
captured_block: PASS
escape_lifetime: PASS
byref_capture: PASS
nested_block: PASS
retain_release: PASS
block_metadata: PASS
```

## 验证命令

```bash
conan create archives/s/swift-corelibs-blocksruntime/6.3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=swift-corelibs-blocksruntime/*
```

## 结论

- 编译状态：通过
- 上游测试用例通过率：`0/0（N/A，上游无测试用例）`
- 新增测试用例通过率：`7/7（100%）`
- 新增测试断言：7 个，全部通过
- 测试运行环境：真实 HarmonyOS PC arm64 环境
