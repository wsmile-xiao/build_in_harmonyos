# HiGHS 1.13.1 — OpenHarmony 预编译包说明

HiGHS 是一款高性能开源线性规划 (LP) 和混合整数规划 (MIP) 求解器。

## 版本信息

- **软件版本**: HiGHS 1.13.1
- **编译日期**: 2026-05-28
- **编译状态**: built ✅
- **构建系统**: CMake
- **目标平台**: OpenHarmony / aarch64 (ARM64)
- **编译器**: Clang 15.0.4 (OpenHarmony 交叉编译工具链)

## 包内容

### highs-1.13.1-ohos-aarch64.tar.gz (17MB, Release 版本)

| 文件路径 | 说明 |
|----------|------|
| `bin/highs` | HiGHS 可执行文件 |
| `include/highs/` | C/C++ 头文件 |
| `include/highs/interfaces/highs_c_api.h` | C API 头文件 |
| `lib/libhighs.a` | 静态库 |
| `lib/` | 共享库和 pkg-config 文件 |

### highs-1.13.1-ohos-aarch64-debug.tar.gz (870KB, Debug 符号包)

包含 Release 版本的调试符号信息。

## 使用方法

### 命令行求解

```bash
highs --model_file input.mps    # 求解 MPS 格式模型
highs --model_file input.lp     # 求解 LP 格式模型
highs --version                  # 查看版本号
```

### C++ API

```cpp
#include "Highs.h"
Highs highs;
highs.addCols(...);
highs.addRows(...);
HighsStatus status = highs.run();
```

### C API

```c
#include "interfaces/highs_c_api.h"
void* highs = Highs_call(...);
```

## 依赖

- **zlib**: 1.3.1 (预编译包已提供)

## 测试结果

- `make test`: 2/2 PASS ✅
  - cxx_examples_call_highs_from_cpp: ✅ (0.11s)
  - c_examples_call_highs_from_c_minimal: ✅ (0.19s)

## 补丁说明

需要应用 `0001-ohc-wrapper.patch`，该补丁为 HiGHS 添加：
1. **configure wrapper** — 将 autotools 风格的 `./configure --prefix=` 转换为 CMake 命令，并添加 `< /dev/null` stdin 重定向以防止 HMDFS 管道 seek 错误
2. **Makefile wrapper** — 将 `make`/`make install`/`make test` 命令转发到 `build` 子目录中的 CMake 构建系统

## 许可证

MIT License — 详见源码包中的 LICENSE.txt