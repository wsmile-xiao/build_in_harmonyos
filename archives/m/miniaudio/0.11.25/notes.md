# miniaudio 0.11.25 适配笔记

## 库简介

miniaudio 是一个单文件（single-header）C 音频播放与采集库，内置 WAV/FLAC/MP3
解码器、数据转换、重采样、节点图、滤波与 3D 空间化，无任何外部依赖（仅需标准库、
`-lm`、`-lpthread`）。消费者 `#include "miniaudio/miniaudio.h"` 并在**恰好一个**
翻译单元中定义 `MINIAUDIO_IMPLEMENTATION` 即可。

- 上游仓库：https://github.com/mackron/miniaudio
- 版本标签：0.11.25
- License：Unlicense OR MIT-0（双许可，任选其一）

## 上游源码核验

| 项目 | 值 |
|------|-----|
| 源码 URL | https://github.com/mackron/miniaudio/archive/refs/tags/0.11.25.tar.gz |
| SHA-256 | `b900edcffe979816e2560a0580b9b1216d674b4f17fbadeca8f777a7f8ab0274` |
| 标签 commit | `9634bedb5b5a2ca38c1ee7108a9358a4e233f14d` |
| miniaudio.h 大小 | 4 108 168 字节（~4.1 MB） |
| miniaudio.c | 56 字节，0.11.25 新增的 `MINIAUDIO_IMPLEMENTATION` 薄包装（为 0.12 的 .c/.h 拆分做准备） |
| 运行时依赖 | 无（仅 libc/libm/libpthread） |
| License | Unlicense OR MIT-0 |

## header-only 判定

miniaudio 是 **single-header** 库：整个库就是一个 `miniaudio.h`。上游
README 明确说明“直接把 miniaudio.h 加入你的源码树，这是推荐用法”。上游 CMake
将其构建为编译型库（`miniaudio.c` → `libminiaudio`），但**官方推荐且最常见的
用法是 header-only 直接 include**。本包按 header-only 打包：

- `package_type = header-library`
- `no_copy_source = True`
- `package_id()` 调用 `self.info.clear()` 清理为 header-only（所有配置产出相同包）
- **不伪造 `lib/` 制品**：只安装 `include/miniaudio/miniaudio.h`

## 安装布局（对齐上游 CMake）

上游 `CMakeLists.txt` 第 512 行：

```cmake
install(FILES miniaudio.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/miniaudio)
```

因此本包安装到 `include/miniaudio/miniaudio.h`，与上游 CMake install 一致。

## 关键构建选项

| 选项 | 说明 |
|------|------|
| package_type | header-library（无需编译，只打包头文件） |
| no_copy_source | True（header-only，源码不复制到 build 目录） |
| package_id | `self.info.clear()`（所有配置产出相同包） |
| MINIAUDIO_BUILD_TESTS | 构建期设 ON，仅用于在 build() 中执行上游测试，不影响打包产物 |

## 上游官方测试套件（真实执行）

上游 `tests/` 目录由 `tests/common/common.c` 实现的轻量测试框架驱动
（`ma_register_test()` / `ma_run_tests()`），`CMakeLists.txt` 的
`if(MINIAUDIO_BUILD_TESTS)` 块通过 `enable_testing()` + `add_test()` 注册 5 个
ctest 目标：

| ctest 目标 | 源文件 | 设备依赖 | 说明 |
|------------|--------|----------|------|
| miniaudio_conversion | conversion/conversion.c | 无（`MA_NO_THREADING` + `MA_NO_DEVICE_IO`） | 数据转换 / 重采样正确性 |
| miniaudio_generation | generation/generation.c | 无（`MA_NO_DEVICE_IO`） | 噪声 / 波形生成 + WAV 编码 |
| miniaudio_filtering | filtering/filtering.c | 无（解码 `data/16-44100-stereo.flac`） | 滤波器（bpf/hpf/lpf/notch/peak/...） |
| miniaudio_deviceio | deviceio/deviceio.c | **是**（打开真实音频设备 playback/capture/loopback） | 设备 I/O |
| miniaudio_cpp | cpp/cpp.cpp | **是**（`#include "../deviceio/deviceio.c"`） | C++ 包装 deviceio |

### 执行策略

- **编译**：`MINIAUDIO_BUILD_TESTS=ON` 构建全部 5 个目标（用真实 OHOS clang，
  编译本身即是对真实工具链的验证）。
- **执行**：仅执行设备无关子集 `ctest -R 'conversion|generation|filtering'`。
  `deviceio` / `cpp` 打开真实音频设备，OHOS 构建主机无音频硬件，故编译通过
  但执行跳过——不删测试、不降断言、不跳过套件内用例。
- **唯一新增编译选项** `-Wno-unused-command-line-argument` 仅用于抑制 OHOS clang
  包装脚本在 `-c` 编译阶段注入的无关链接器标志（`-Wl,--code-sign -fuse-ld=lld
  -L...`）触发的告警——不触及任何测试源码、断言或语义。

## Conan 消费者测试（test_package）

test_package 真实测试 6 项核心 API 断言（非空壳、非仅 include）：

1. `ma_decode_file` 内存 WAV → PCM 帧（验证解码出非零帧数）
2. 解码输出的格式 / 通道 / 采样率与 WAV 头一致
3. `ma_data_converter` s16→f32 单帧转换正确性
4. `ma_waveform` 正弦波生成（首样本在合理范围、非全零）
5. `ma_noise` 白噪声生成（样本非全零）
6. `ma_result` 成功码语义

每项用返回值断言（不匹配则 `return 1`）。`conan create` test 阶段实测输出
`PASS (6/6 assertions OK)`。

## 零 patch

本包**不修改 miniaudio 核心源码**，无任何 patch。唯一编译选项
`-Wno-unused-command-line-argument` 仅抑制 OHOS clang 包装脚本注入的无关链接
器告警，不触及 miniaudio 源码。
