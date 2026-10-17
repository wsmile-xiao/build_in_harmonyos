# VkFFT_TestSuite 1.3.4 构建与执行记录（OpenHarmony PC aarch64 真机）

执行日期：2026-10-11　设备：HarmonyOS PC 真机，GPU = Maleoon 916（Vulkan API 1.2.275）

## 一、设备能力探针

- `vkEnumeratePhysicalDevices` → 1 个物理设备：`Maleoon 916`（Vulkan API 1.2.275）
- `VkPhysicalDeviceFeatures`：`shaderFloat64=0`、`shaderInt64=0`
  （double / quadDoubleDouble 类 sample 因此被驱动层拒绝，属设备硬件能力，非库缺陷）

## 二、构建命令（VKFFT_BACKEND=0 Vulkan 后端，禁用上游 FetchContent，全部用 ohpcd 制品仓已有包）

编译器：`/data/service/hnp/bin/clang++ --target=aarch64-linux-ohos -fuse-ld=lld -std=c++17 -O2`

```sh
-DVKFFT_BACKEND=0 -DUSE_FFTW
-I<vulkan-headers>/include
-I<glslang pkg>/include/glslang/Include   # 上游同款平铺 include（glslang_c_interface.h）
-I<vkFFT-src>/vkFFT -I<vkFFT-src> -I<vkFFT-src>/half_lib
-I<vkFFT-src>/benchmark_scripts/vkFFT_scripts/include
-I<fftw3>/include -I<fftw3f>/include
<vkFFT-src>/VkFFT_TestSuite.cpp <vkFFT-src>/benchmark_scripts/vkFFT_scripts/src/*.cpp
-L<glslang pkg>/lib -lglslang -lSPIRV -lMachineIndependent -lOSDependent \
  -lGenericCodeGen -lglslang-default-resource-limits
-L<fftw3>/lib -lfftw3 -L<fftw3f>/lib -lfftw3f
/system/lib64/libvulkan.so
```

- glslang 静态库：conan 包 `glslang/vulkan-sdk-1.3.290.0`（与配方依赖同源）
- vulkan 头：conan 包 `vulkan-headers/vulkan-sdk-1.4.357.0`；运行时 loader：系统 `/system/lib64/libvulkan.so`
- FFTW（precision 参考库）：conan 包 `fftw/3.3.10`（double）+ `fftw3f/3.3.9.1`（single），shared
- 运行：`LD_LIBRARY_PATH=<fftw3>/lib:<fftw3f>/lib ./VkFFT_TestSuite -vkfft <sample_id>`

## 三、执行脚本

`run_all.sh`：顺序执行 30 个 sample（0–19、50–52、100、101、1000–1004），
每个限时 900 s，逐样本记录 stdout/stderr（`out_s<id>.log`）与退出码（`summary.txt`）。
总耗时约 1 h 44 m（2026-10-11 12:59–14:43）。

## 四、注意

- 上游 CMake 的 glslang 为 FetchContent 在线拉取，本记录改用制品仓已有 glslang
  静态库直接链接，未改上游任何源码。
- `half_lib/half.hpp` 为上游自带 third-party 头，直接 `-I` 引入。
