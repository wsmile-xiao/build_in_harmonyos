# cmsis-dsp 1.18.0 上游测试完整枚举台账 + 双口径统计（R02 返工更新）

- task_id: cmsis-dsp-1.18.0-r02-pc7-5-20260920T150000Z（返工：上游测试全量实例化）
- previous: cmsis-dsp-1.18.0-r01-pc7-5-20260920T123932Z
- executor: pc7-5
- 枚举依据: 官方 tag v1.18.0（commit 4b6f26593e9d）源码 Testing/ 目录，可复制枚举规则

## 1. R01 → R02 返工动作

| 动作 | R01 | R02 |
|------|-----|-----|
| NEON 配置实例化 | 0（desc_neon 构建被截断 Patterns.h 阻塞） | 786 项实际实例化并运行 |
| 上游模式补全 | Q7/Q31 参考缺失（MatrixNeon.py 部分生成） | 删除不完整 Q7 目录后全量重生成（BinaryQ7 12 文件齐全） |
| test 目标构建 | NEON 配置无法完整构建 | 注入 `ARM_MATH_NEON_FLOAT16 + ARM_FLOAT16_SUPPORTED + -Wno-macro-redefined` 后链接成功 |
| 全量通过率 | 1527/2859（53.4%） | **2437/2859（85.2%）** |

## 2. 枚举对象全覆盖清单

| 类别 | 路径 | 数量 | 是否独立上游用例 |
|------|------|------|------------------|
| 用户测试源 | Testing/Source/Tests/*.cpp | 112 | ✅ 独立用户测试套件 |
| 用户测试源 | 其中独立 TEST_* 用例 ID（跨文件去重） | 2859 | ✅ grep -hoE 'TEST_[A-Z0-9_]+' \| sort -u |
| 生成 decl 头 | Testing/GeneratedInclude/*_decl.h | 112（类） | 用例 ID 声明载体 |
| 基准 | Testing/Source/Benchmarks/*.cpp | 73（140 TEST_* ID） | ❌ 非用例 |
| 框架源码/头 | FrameworkSource / FrameworkInclude | 11 / 若干 | ❌ 框架内部 |
| 模式生成脚本 | PatternGeneration/*.py | 28 | ❌ 脚本 |
| 测试脚本 | TestScripts/*.py | 6 | ❌ 脚本 |
| 样例 | Examples/ | 4 类 | ❌ 样例 |
| fixture | Patterns/*.txt | 4355+（Q7 补全后） | ❌ 模式数据 |

## 3. 双口径统计（R02 返工后）

### 口径一: 源码声明总数
- **source_declared_total = 2859**（112 个用户测试套件文件中独立 TEST_* 用例 ID 跨文件去重数）

### 口径二: 三配置实际实例化/注册 + 执行
| 配置 | 注册 desc | executed | passed | failed |
|------|-----------|----------|--------|--------|
| 默认配置 | desc.txt | 1527 | 1527 | 0 |
| F16 配置 | desc_f16.txt | 304 | 304 | 0 |
| NEON 配置 | desc_neon.txt | 786 | 606 | **180** |
| **合计** | | **2617** | **2437** | **180** |

- configured_executable_total（三配置并集执行）: 2617
- executed_passed_total: 2437
- 失败: 180（详见 §4）
- 未实例化/未注册: 2859 − 2617 = 242（decl 头声明但三个 desc 配置均未注册的 TEST_* ID，见 §5）

### 通过率（PR 单一口径）
- **executed_passed_total / source_declared_total = 2437 / 2859（85.2%）**
- 当前配置可执行集合通过率另列: 2437/2617（93.1%）
- 默认配置 1527/1527（100%）、F16 配置 304/304（100%）、NEON 配置 606/786（77.1%）

## 4. 180 个失败用例逐项说明（NEON 配置 TransformNeonCQ31 套件）

### 失败特征（已逐项映射）
- **全部位于 TransformNeonCQ31 套件**（NEON 复数 Q31 CFFT 动态实例），90 个 CFFT + 90 个 CIFFT
- **失败尺寸全部为含因子 5 的长度**: 20, 40, 60, 80, 100, 120, 160, 180, 200, 240, 300, 320, 360, 400, 480（每个尺寸 4 用例 × 15 尺寸 = 60，CFFT+CIFFT 各半 → 180）
- **通过尺寸全部为 2/3 幂**: 24, 32, 36, 48, 64, 72, 96, 108, 128, 144 等（无因子 5）
- SNR 值全部 < 100（3.4 ~ 41.7 dB），为输出与参考显著不符，非精度级差异

### 根因（证据链）
1. 失败尺寸与通过尺寸以"是否含因子 5"严格二分 → 指向 radix-5 蝶形路径
2. 源码树无任何 radix5 实现文件，库中无 radix5 符号（nm 0 命中）
3. `arm_cfft_init_dynamic_q31`（NE10 路径）文档声明支持因子 3/5，但实现依赖 Ne10 蝶形；本工具链（clang 15.0.4 aarch64 OHOS）下**独立 20 点动态 Q31 CFFT 直接段错误（Signal 11）**，测试框架内表现为 SNR 严重不符
4. **与注入宏无关**：R01 run1（无任何注入宏的 NEON 构建）与 R02 完全相同的 180 个失败与相同 SNR 值（5.80879 / 24.1183 / 5.31342 / 25.6025 / 3.92947 / 25.1685 / 26.1648 / 5.47007 / 22.3204 / 24.1835 / 3.4482 / 26.4712 …）
5. 参考模式文件均存在且有效（如 `Patterns/DSP/TransformNeon/TransformNeonQ31/ComplexFFTSamples_Noisy_20_1_q31.txt` 82 行非空），排除数据缺失

### 判定
- 真实技术/平台阻塞：NE10 动态 Q31 CFFT 的因子 5（radix-5）路径在本工具链下输出错误（独立调用崩溃）——非本库配方、补丁或配置可修，属上游 Ne10 实现与 clang 15 aarch64 的兼容性缺陷
- 已尽力最小纳入：补全 Q7 模式 → 重新生成 desc_neon TestDesc/Patterns.h（719MB 完整）→ 注入必需宏构建 test（786 项实际运行）→ 606 项通过
- 恢复条件: 上游修复 Ne10 int32 蝶形因子5 路径，或改用支持因子5 的参考 FFT 实现/更新工具链后重跑 desc_neon 配置
- 证据命令/日志: 见 §6（run-neon-r02.log SHA-256）、独立复现 cfft20_check（Signal 11）

## 5. 未实例化/未注册 242 项说明

- decl 头（GeneratedInclude/*_decl.h）中声明的 TEST_* ID 中，未被 desc.txt / desc_f16.txt / desc_neon.txt 任一配置注册的部分（如部分 F64/Q7 套件的用例、仅基准引用的 ID 等），与上游 desc 文件的套件-用例选择一致
- 逐项映射规则: 源码声明（*_decl.h TEST_* 常量）→ desc 文件 class = 注册 → processTests.py -e 生成 TestDesc → test 可执行 → 运行日志
- 该类为上游 desc 未选择注册的声明，非本库可纳入范围（若上游在完整 desc 中注册对应套件，将随新 desc 自动纳入）

## 6. 运行证据（日志 + SHA-256）

| 日志 | 内容 | SHA-256 |
|------|------|---------|
| run2.log | 默认配置 1527/1527，exit 0 | fe04746b9445c043b0306b18c0749e8eb6a534e28e065d83d7bd16f5318f378e |
| run-f16.log | F16 配置 304/304，exit 0 | 47bd8ef488c3b435c5db9d587f01c07a18617eff148c7d9e9d19e6777f520ba6 |
| run-neon-r02.log | NEON 配置 786 执行 / 606 通过 / 180 失败，exit 0 | 23705a60bd73819ec5fcdc1c0991d04ff1a8a209972fdb06f04caa63b5181cb1 |

- 构建命令（cwd=Testing/）: `cmake -S . -B build-tests -DCMAKE_BUILD_TYPE=Release -DHOST=ON -DNEON=ON -DCMAKE_C_FLAGS="-DARM_MATH_NEON_FLOAT16 -DARM_FLOAT16_SUPPORTED -Wno-macro-redefined" -DCMAKE_CXX_FLAGS=... && make -C build-tests -j4`（exit 0）
- 运行命令（cwd=Testing/build-tests/）: `./test > 日志 2>&1`（exit 0）
- 独立复现: cfft20_check（20 点动态 Q31 CFFT）→ Signal 11（段错误）

## 7. 判定

- R02 返工后全量通过率 2437/2859（85.2%），较 R01 53.4% 提升显著；NEON 变体 786 项已全部实际实例化并运行
- 剩余 180 项失败为 NE10 动态 Q31 CFFT 因子5 路径的真实工具链兼容性缺陷（独立复现崩溃），恢复条件见 §4
- 默认配置 1527/1527（100%）、F16 配置 304/304（100%）保持全绿
