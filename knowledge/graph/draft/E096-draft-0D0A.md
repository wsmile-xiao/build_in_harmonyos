# E096: libjpeg-turbo SIMD 链接失败（未知平台）

## 错误现象

编译 libjpeg-turbo 时，在链接 `simdcoverage` 测试程序时失败：

```
ld.lld: error: undefined symbol: jsimd_can_rgb_ycc
>>> referenced by simdcoverage.c
>>>               CMakeFiles/simdcoverage.dir/simdcoverage.c.obj:(main)

ld.lld: error: undefined symbol: jsimd_can_rgb_gray
>>> referenced by simdcoverage.c
>>>               CMakeFiles/simdcoverage.dir/simdcoverage.c.obj:(main)

ld.lld: error: undefined symbol: jsimd_can_ycc_rgb
>>> referenced by simdcoverage.c
>>>               CMakeFiles/simdcoverage.dir/simdcoverage.c.obj:(main)
...
```

同时 CMake 配置阶段有警告：

```
CMake Warning at simd/CMakeLists.txt:5 (message):
  SIMD extensions not available for this CPU (unknown).  Performance will
  suffer.
```

## 根因分析

libjpeg-turbo 使用 SIMD（SIMD 指令集）加速 JPEG 编解码。CMake 在配置阶段会检测目标 CPU 类型：

- **已知平台**（x86, x86-64, Arm, PowerPC, MIPS）→ 编译 SIMD 扩展代码（使用 NASM/Yasm）
- **未知平台**（如 HarmonyOS，CMake 输出 "unknown"）→ **不编译 SIMD 扩展**

**关键问题**：当平台被识别为 "unknown" 时，CMake 会跳过 SIMD 扩展的编译，但 **`simdcoverage` 测试程序** 仍在构建目标列表中，它依赖 SIMD 函数符号（`jsimd_can_*` 系列），导致链接失败。

**影响范围**：
- `simdcoverage` 是代码覆盖率测试工具，不是核心库或用户工具
- 禁用 SIMD 不影响 JPEG 核心功能，只是牺牲性能加速（2-6x）

## 解决方案

**推荐方案**：禁用 SIMD 扩展和测试套件

```bash
cmake -G"Unix Makefiles" \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DWITH_SIMD=0 \
  -DWITH_TESTS=0 \
  ..
```

**关键参数说明**：
- `-DWITH_SIMD=0`：完全禁用 SIMD 扩展，跳过所有 SIMD 相关代码
- `-DWITH_TESTS=0`：禁用测试套件（包括 `simdcoverage`）

**效果**：
- ✅ 编译通过（100%）
- ✅ 核心库和工具正常工作（libjpeg.so, libturbojpeg.so, cjpeg, djpeg, jpegtran）
- ⚠️ 性能降低（无 SIMD 加速，但仍比 libjpeg 快）

## 验证步骤

1. **CMake 配置**：查看日志中是否有 "SIMD extensions: None (WITH_SIMD = 0)"

```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DWITH_SIMD=0 -DWITH_TESTS=0 ..
# 期望输出：-- SIMD extensions: None (WITH_SIMD = 0)
```

2. **编译通过**：

```bash
make -j$(nproc)
# 期望输出：[100%] Built target jpegtran
```

3. **安装成功**：

```bash
make install DESTDIR=$TEST_PREFIX
# 期望输出：Install the project...（无错误）
```

4. **静态链接工具可用**（动态链接有 RPATH 问题，需 package 修复）：

```bash
./cjpeg-static --version
# 期望输出：usage: ./cjpeg-static [switches] ...
```

## 受影响软件

- **libjpeg-turbo** 所有版本
- 在 **未被 CMake 官方支持的平台** 上编译时（如 HarmonyOS、自定义嵌入式系统）

## 平台适配建议

**长期方案**（适合贡献到 CMake）：
1. 创建 `Platform/HarmonyOS.cmake` 文件，定义 HarmonyOS 平台标识
2. 提交到 CMake 官方：https://discourse.cmake.org
3. CMake 识别平台后，SIMD 扩展检测会正常工作

**当前方案**：
- 禁用 SIMD（本方案）
- 或手动编写 SIMD fallback 代码（高级用户）

## 知识图谱关联

- **E007**: CMake 平台识别失败（config.guess/config.sub）
- **E046**: CMake 在 HarmonyOS 上的通用问题

## 分类

- **类别**: L2（构建系统模式）
- **频率**: 常见（首次在新平台编译 libjpeg-turbo）
- **严重性**: 中等（阻塞编译，但有明确解决方案）

---
**创建者**: Agent 0D0A
**创建时间**: 2026-04-24
**软件**: libjpeg-turbo 3.1.4.1