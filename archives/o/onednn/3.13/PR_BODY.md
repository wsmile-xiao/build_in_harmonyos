## PR 信息
- **三方库名称**：onednn
- **上游版本**：3.13
- **上游仓库地址**：https://github.com/uxlfoundation/oneDNN
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1552 | 来源：tests/gtests（审查实测 N=1552，gtest TEST/TEST_P） |
| 集成测试 | 0 | benchdnn 为独立基准套件 |
| 其他测试 | 0 | |
| **合计** | **1552** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1552 | 不变 | `ONEDNN_BUILD_TESTS=ON`，真机 ctest 63 个 gtest 二进制 |
| 集成测试 | 0 | 不变 | |
| 鸿蒙特有测试 | 1 | 新增 | test_package 消费者：创建 CPU engine |
| **合计** | **1553** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

鸿蒙特有测试为 Conan 消费者契约，不替代上游 gtest。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：58/63 二进制（92%；审查口径分母 1552，见下）
- 新增测试用例通过率：1/1（100%）

真机 `ONEDNN_CPU_RUNTIME=OMP` + `ONEDNN_ENABLE_WORKLOAD=TRAINING`，ctest 63 个 gtest 二进制 **58 通过 / 5 失败**。相对 SEQ+INFERENCE（45/63）已尽量抬高。

未达 1552/1552 的 5 个二进制及技术原因（AArch64 HarmonyOS，无法靠配方变成 x64 ISA）：

1. `test_pooling_forward` / `test_pooling_backward`：SEGFAULT，`TestPooling3D_ndhwc_CPU` 3D pooling JIT 在 musl/OHOS 上崩溃
2. `test_reorder`：12 个 `PaddedWeights_CPU` 用例失败，测的是 x64 blocked 权重格式（nChw16c 等），AArch64 无对应 layout
3. `test_eltwise` / `test_api`：单二进制内 TEST_P 过多，600s 仍 Timeout（AArch64 参考实现慢）

无法把上述 x64 格式/3D pooling crash 变成 PASS。OpenMP+TRAINING 已使 backward/softmax/lrn/prelu/resampling/gemm_bf16 等由 FAIL 变为 PASS。

## 补充说明

- AArch64，CPU runtime OpenMP（libomp 5.0），workload TRAINING，无 ACL/GPU/graph
- musl 无 `_SC_LEVEL*_CACHE_SIZE`，配方写死 L1/L2
- `CMAKE_POSITION_INDEPENDENT_CODE=ON`
- 验证命令：`conan create archives/o/onednn/3.13 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
