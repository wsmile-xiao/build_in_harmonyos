# cmsis-dsp 1.18.0 — 消费者用例 + HarmonyOS 专项测试运行证据

task_id: cmsis-dsp-1.18.0-r01-pc7-5-20260920T123932Z · executor: pc7-5 · 平台: HarmonyOS PC (aarch64), clang 15.0.4

## 1. 消费者用例（业务上层组件视角）

- 源文件: `archives/c/cmsis-dsp/1.18.0/reports/consumer.c`
- 使用方式: 仅包含库已安装/导出的公开头 `arm_math.h`（安装目录 `include/CMSIS-DSP/`），链接 `libCMSISDSP.a`
- 编译命令（cwd=/storage/Users/currentUser/tmp）:
  ```
  clang -O2 -D__GNUC_PYTHON__ -o cmsis-dsp-consumer \
    -I/storage/Users/currentUser/tmp/test-install-cmsis-dsp-1.18.0/storage/Users/currentUser/usr/local/include/CMSIS-DSP \
    /storage/Users/currentUser/pd/worktrees/cmsis-dsp/archives/c/cmsis-dsp/1.18.0/reports/consumer.c \
    /storage/Users/currentUser/tmp/test-install-cmsis-dsp-1.18.0/storage/Users/currentUser/usr/local/lib/libCMSISDSP.a -lm
  ```
- 编译退出码: 0
- 运行命令（cwd=/storage/Users/currentUser/tmp）: `./cmsis-dsp-consumer`，退出码 **0**
- 调用的公开 API: `arm_rms_f32`（统计函数组，公开头导出）
- 验证结果: 输入 ±1 方波 8 点 → RMS=1.000000，断言 |rms−1|<1e-4 通过，输出 "consumer: cmsis-dsp 1.18.0 公开 API arm_rms_f32 验证通过"

## 2. HarmonyOS 专项测试

- 源文件: `archives/c/cmsis-dsp/1.18.0/reports/harmonyos-test.c`
- 编译命令（cwd=/storage/Users/currentUser/tmp）:
  ```
  clang -O2 -D__GNUC_PYTHON__ -o cmsis-dsp-harmonyos-test \
    -I/storage/Users/currentUser/tmp/test-install-cmsis-dsp-1.18.0/storage/Users/currentUser/usr/local/include/CMSIS-DSP \
    /storage/Users/currentUser/pd/worktrees/cmsis-dsp/archives/c/cmsis-dsp/1.18.0/reports/harmonyos-test.c \
    /storage/Users/currentUser/tmp/test-install-cmsis-dsp-1.18.0/storage/Users/currentUser/usr/local/lib/libCMSISDSP.a -lm
  ```
- 编译退出码: 0
- 运行命令（cwd=/storage/Users/currentUser/tmp）: `./cmsis-dsp-harmonyos-test`，退出码 **0**
- 8 组断言全部通过:
  1. arm_negate_f32 一致性
  2. arm_abs_f32 一致性
  3. arm_mean_f32 正弦均值≈0
  4. arm_var_f32 正弦方差≈0.5
  5. arm_std_f32 与 sqrt(var) 一致
  6. arm_fir_f32 峰值(0.9437)与移动平均理论频响(0.944)一致
  7. RFFT 能量集中在 3 周期 bin
  8. 矩阵乘法数值正确（arm_mat_mult_f32: [[1,2],[3,4]]×[[5,6],[7,8]]=[[19,22],[43,50]]）
- 调用的公开 API: arm_negate_f32 / arm_abs_f32 / arm_mean_f32 / arm_var_f32 / arm_std_f32 / arm_fir_init_f32 / arm_fir_f32 / arm_rfft_fast_init_f32 / arm_rfft_fast_f32 / arm_mat_init_f32 / arm_mat_mult_f32
- 输出: "PASS: HarmonyOS 专项测试 全部通过 (8 组断言)"

## 3. 说明

- `-D__GNUC_PYTHON__` 是上游文档明确的免 CMSIS-Core（cmsis_compiler.h）构建要求；
  安装的 CMake 包（CMSISDSPTargets）通过 INTERFACE_COMPILE_DEFINITIONS 自动传播该定义，
  裸 clang 消费时需显式给出（与上游 arm_math_types.h 注释一致）。
- 消费者用例与上游测试、鸿蒙专项测试分别计数，未重复充数。
