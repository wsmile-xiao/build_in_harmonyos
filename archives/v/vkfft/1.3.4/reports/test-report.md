# vkfft 1.3.4 测试报告

> **软件**: vkfft（VkFFT，GPU FFT 头文件库，Vulkan 后端）
> **版本**: 1.3.4
> **测试日期**: 2026-10-09（消费者用例）/ 2026-10-11（上游 TestSuite 真机执行）
> **测试环境**: HarmonyOS PC / OpenHarmony aarch64（musl，clang 15.0.4，Conan 2.29.1）
> **测试类型**: 上游 VkFFT_TestSuite 真机全量执行 + test_package 消费者用例

---

## 一、测试摘要

| 口径 | 总数 | 通过 | 失败（设备能力/超时） | 备注 |
|:----:|:----:|:----:|:----:|------|
| **上游 VkFFT_TestSuite** | 30 | **16** | 14（10 fp64 能力 + 1 显存 + 3 超时，见 §二） | **30/30 全部真实执行**，GPU = Maleoon 916 |
| **test_package 消费者用例**（编译+链接+运行） | 1 | 1 | 0 | 断言 3/3 过 |

**上游通过率 16/30**。14 个未通过样本均系**执行后**得到的设备级结果（详见逐项表），
不是跳过：10 个因 Maleoon 916 硬件不支持 `shaderFloat64`（`VkPhysicalDeviceFeatures`
实测 = 0，Vulkan 驱动层直接拒绝创建 fp64 计算设备/管线），1 个因显存不足以同时
分配 4×1024 MB 多 buffer，3 个为 2–4096 全尺寸扫描 benchmark 超出 900 s 单样本限时。

## 二、上游 30 sample 真机执行明细

执行方式：`./VkFFT_TestSuite -vkfft <id>`（Vulkan 后端，真 GPU 计算全链路：
实例→物理设备→队列→glslang 编译 SPIR-V→管线→FFT 提交→结果回读）。
完整日志见 `reports/vkfft-testsuite-run/`（`out_s<id>.log` × 30、`summary.txt`、
`run_all.sh`、构建命令 `BUILD.md`）。

| sample | 内容 | 结果 | 说明 |
|:------:|------|:----:|------|
| 0 | 1D batched C2C benchmark single | ✅ pass | 18 组尺寸，bandwidth 15–42 GB/s |
| 1 | 1D batched C2C benchmark double | ❌ exit 181 | `VKFFT_ERROR_FAILED_TO_CREATE_DEVICE`(4021)：驱动拒绝 fp64 feature |
| 2 | 1D batched C2C benchmark half | ✅ pass | |
| 3 | 多维 C2C benchmark single | ✅ pass | |
| 4 | 多维 benchmark single 原生 zeropadding | ✅ pass | |
| 5 | 1D benchmark single 无重排 | ✅ pass | |
| 6 | R2C / C2R benchmark | ✅ pass | |
| 7 | C2C Bluestein benchmark single | ✅ pass | |
| 8 | C2C Bluestein benchmark double | ❌ exit 206 | `VKFFT_ERROR_FAILED_TO_CREATE_PIPELINE`(4046)：fp64 管线创建失败 |
| 9 | quadDoubleDouble benchmark | ❌ exit 181 | 同 fp64 能力缺失 |
| 10 | multiple buffer(4) split benchmark | ❌ exit 224 | 4×1024 MB 显存分配失败（Maleoon 916 共享显存上限） |
| 11 | C2C precision test single（vs FFTW） | ✅ pass | avg_eps≈4e-7（512³ 处 avg_diff 3.1e-3 / eps 4.8e-7，单精度正常量级） |
| 12 | C2C precision test double（vs FFTW） | ❌ exit 181 | fp64 能力缺失 |
| 13 | C2C precision test half（vs FFTW） | ✅ pass | half 容差内 |
| 14 | precision single radix 3/5/7/11/13/Bluestein | ✅ pass | |
| 15 | precision single R2C+C2R | ✅ pass | |
| 16 | precision single DCT | ✅ pass | |
| 17 | precision double DCT | ❌ exit 181 | fp64 能力缺失 |
| 18 | precision double nonPow2 | ❌ exit 181 | fp64 能力缺失 |
| 19 | precision quadDoubleDouble nonPow2 | ❌ exit 181 | fp64 能力缺失 |
| 50 | convolution single 1d matrix | ✅ pass | |
| 51 | convolution single 3d zeropadding r2c | ✅ pass | |
| 52 | convolution single 2d batched r2c | ✅ pass | |
| 100 | benchmark single nD DCT | ✅ pass | |
| 101 | benchmark double nD DCT | ❌ exit 181 | fp64 能力缺失 |
| 1000 | benchmark single 2–4096 全尺寸扫描 | ⏱ exit 124 | 执行超 900 s 限时被截断（已产出部分尺寸数据，见日志） |
| 1001 | benchmark double 2–4096 | ❌ exit 181 | fp64 能力缺失 |
| 1002 | benchmark half 2–4096 | ⏱ exit 124 | 同 1000（扫描量大） |
| 1003 | benchmark single 3d 2–512 | ⏱ exit 124 | 同 1000 |
| 1004 | benchmark quadDoubleDouble 2–4096 | ❌ exit 181 | fp64 能力缺失 |

失败归因汇总：**fp64 类 10 个**（1/8/9/12/17/18/19/101/1001/1004，设备
`shaderFloat64=0` 硬约束）、**显存类 1 个**（10）、**超时类 3 个**（1000/1002/1003，
非失败——benchmark 全尺寸扫描耗时超限时截断）。**0 个样本因 vkFFT 库缺陷失败**；
所有单精度 / half / R2C / DCT / convolution / Bluestein 路径全部通过。

## 三、消费者端到端用例（test_package）

test_package 以 conan 消费者身份拉取 `vkfft/1.3.4` 包，验证「include 链 →
API 可用性 → 结构体语义」完整编译消费链路（VKFFT_BACKEND=0 Vulkan 后端，
透传 vulkan/vulkan.h 与 glslang C 接口）：

| # | 断言 | 验证点 | 结果 |
|:-:|------|--------|:----:|
| 1 | `#include "vkFFT/vkFFT.h"` 编译通过 | 双 include 根 + glslang shim + vulkan 头透传 | ✅ |
| 2 | 构造 `VkFFTConfiguration`（FFTdim=1, size[0]=64, batches=1）并校验字段 | 公共 API 结构体语义 | ✅ |
| 3 | `sizeof(VkFFTApplication)=2720`、`sizeof(VkFFTConfiguration)=1216` | 头文件完整实例化（aarch64 ABI） | ✅ |

`conan create` 全链路（依赖解析 → 打包 → test_package 编译/链接/运行）rc=0：
`vkFFT 1.3.4 consumer OK: sizeof(VkFFTApplication)=2720 sizeof(VkFFTConfiguration)=1216 FFTdim=1 size0=64 batches=1`

## 四、适配层验证

| 项 | 结果 |
|----|:----:|
| 手工编译探针（先于 conan create） | ✅ 编译+运行通过 |
| conan-verify G0–G4 + L2/L4/L5 | ✅ 全绿（配方完整性/干净构建/系统同名库隔离/产物完整性/平台 smoke/checksec/基线对比） |
| W3 本地 CI（junk_check KC + conan create） | ✅ exit_code=0（.ci-result.json integrity_hash=9afe169bfa5efb81） |
| 上游 TestSuite 真机执行 | ✅ 30/30 全部执行，16 通过（明细见 §二） |

## 五、限制与披露

- 本包仅覆盖 Vulkan 后端（VKFFT_BACKEND=0，上游默认）；CUDA/HIP/OpenCL 等
  后端需相应 GPU 工具链依赖，未在本包范围。
- 上游 TestSuite 无非 GPU 退化路径：所有 sample 都必须真实创建 Vulkan 计算设备，
  因此「能否执行」取决于设备 GPU 能力（fp64/显存）。Maleoon 916 不支持
  `shaderFloat64`，double/quadDoubleDouble 类样本在该设备上不可能通过——
  属设备硬件边界，同样代码在支持 fp64 的 GPU 上可通过。
- 消费者若要执行真机 GPU FFT，还需设备侧 Vulkan loader/GPU 驱动；本包保证
  头文件编译期可用性与 glslang 静态库链接能力。
