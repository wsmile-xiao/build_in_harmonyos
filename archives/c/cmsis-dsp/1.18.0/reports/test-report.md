# cmsis-dsp 1.18.0 测试报告（R02 返工更新）

task_id: cmsis-dsp-1.18.0-r02-pc7-5-20260920T150000Z（R01 → R02 返工后）· executor: pc7-5 · 平台: HarmonyOS PC (aarch64), clang 15.0.4

## 1. 编译验证
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18 工具链 `/data/service/hnp/bin/clang`）
- 构建系统: CMake（`-DHOST=ON -DNEON=ON -DCMSISDSP_INSTALL=ON`，HOST=ON → `__GNUC_PYTHON__` 免 CMSIS-Core）
- 状态: `built`（conan-verify G0-G4 + L2/L4/L5 全部通过；W3 本地 CI pass）
- NEON test 目标: 注入 `ARM_MATH_NEON_FLOAT16 + ARM_FLOAT16_SUPPORTED + -Wno-macro-redefined` 后链接成功（786 项实例化）

## 2. 测试汇总
| 测试面 | 结果 | 证据 |
|--------|------|------|
| Conan test_package（R34 实质 API 测试） | PASS（3 API 数值断言） | test_package/test.c |
| 消费者用例（arm_rms_f32） | PASS exit 0 | reports/consumer-run.md |
| HarmonyOS 专项测试（8 组断言） | PASS exit 0 | reports/harmonyos-test.c + consumer-run.md |
| 上游测试默认配置（desc.txt） | 1527/1527 通过（100%） | reports/test-enumeration-ledger.md §6 |
| 上游测试 F16 配置（desc_f16.txt） | 304/304 通过（100%） | reports/test-enumeration-ledger.md §6 |
| 上游测试 NEON 配置（desc_neon.txt） | 786 执行 / 606 通过 / 180 失败 | reports/test-enumeration-ledger.md §4、§6 |

## 3. 上游测试双口径（R02 返工后）
- source_declared_total: **2859**（Source/Tests 112 个用户测试套件中独立 TEST_* 用例 ID 去重）
- 三配置合计 executed=2617，passed=2437，failed=180
- 全量口径: **2437/2859（85.2%）**，可执行集合 2437/2617（93.1%）；默认 1527/1527（100%）、F16 304/304（100%）
- 180 个失败逐项映射: TransformNeonCQ31 套件全部含因子 5 尺寸（20/40/60/80/100/120/160/180/200/240/300/320/360/400/480），90 CFFT + 90 CIFFT，SNR < 100
- 180 个失败根因: NE10 动态 Q31 CFFT（arm_cfft_init_dynamic_q31）因子5（radix-5）路径在本工具链下输出错误/独立复现段错误（Signal 11）；与注入宏无关（R01 无宏构建同 180 失败同 SNR）；恢复条件见台账 §4
- 未实例化/未注册: 242（desc 未注册的声明 ID，见台账 §5）

## 4. 结论
R02 返工后 NEON 变体 786 项全部实际实例化并运行，全量通过率由 R01 的 1527/2859（53.4%）提升至 2437/2859（85.2%）。180 个失败为 NE10 动态 Q31 CFFT 因子5 路径的真实工具链兼容性缺陷（独立复现崩溃），恢复条件已在台账 §4 列明。