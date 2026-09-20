# libelas 20150630 — HarmonyOS PC 适配说明

## 概况

libelas（LIBrary for Efficient LArge-scale Stereo matching）从校正后的灰度立体像对
计算视差图（`Elas::process`）。小型 C++ 库，内层循环是手写 x86 SSE2 内建。

- 上游：http://www.cvlibs.net/software/libelas/ （源码取自 Debian non-free orig tarball）
- 形态：**库 + demo 可执行**
- 许可证：GPL-3.0-or-later（随库附带的 SSE2NEON 为 MIT）
- 依赖：无（SSE2NEON 随包提供，非系统依赖）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | **x86 专用（SSE2/SSE3）** | `elas.h`/`descriptor.cpp` 无条件 `#include <emmintrin.h>`，`elas.cpp` 用 `_mm_*`，CMakeLists 硬编码 `-msse3`；Debian 也只出 amd64 二进制。补丁在非 x86 上改为包含 **SSE2NEON v1.8.0**（DLTcollab，MIT），它把本库用到的全部 22 个内建映射到 NEON |
| 2 | 头文件暴露 `__m128i` | `elas.h` 私有方法签名用到 `__m128i` → `sse2neon.h` 必须随 `elas.h` 一起安装，消费者才能编译 |
| 3 | 上游 CMake 会清空 flags | `SET(CMAKE_CXX_FLAGS "-msse3")` 覆盖工具链 flags → 绕过 CMake，直接用 OHOS clang++ 编译 5 个源文件为 `libelas.so`/`.a` |
| 4 | demo 的 `max()` | libc++ 不经 `<iostream>` 传递 `<algorithm>` → 编译 demo 时加 `-include algorithm` |
| 5 | 拉取 SSE2NEON | `source()` 从 `codeload.github.com` 取 pinned tag v1.8.0（github.com 在真机常不可达） |

## 测试

### 上游

上游无测试框架，但 README 记录的验证是 `./elas demo`：处理随包的 7 组 `img/*.pgm`
并写出左右视差图。`build()` 复制 `img/` 到构建目录并执行 `./elas demo`，
要求产出 14 个 `*_disp.pgm`（7 对 × 左右），日志写入 `upstream-elas-demo.log`。

### 消费者测试（test_package，CMake + ctest）

`test_package/test_libelas.cpp` 共 6 条断言：合成一张高纹理图并生成"右图 = 左图
右移 6px"的像对，调用 `Elas::process` 后统计内部区域视差——要求多数像素有视差、
多数与已知位移 6±1 吻合、有效均值在 1px 内、左右视差图非空。

## 已知限制

- SSE2NEON 属第三方移植层；数值结果与 x86 版本可能有一位以内差异（消费者测试用
  1px 容差）。
- `subsampling` 与 MATLAB MEX 包装未验证。
