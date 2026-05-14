# libcerf — OpenHarmony/HarmonyOS 预编译包

## 软件简介

libcerf 是一个数值计算库，提供复数误差函数及相关数学函数的高精度实现。主要用于科学计算、光谱分析和物理学研究。

**核心功能**:
- `cerf`: 复数误差函数
- `cerfc`: 复数互补误差函数
- `cdawson`: 复数 Dawson 积分
- `erfcx`: 缩放互补误差函数
- `erfi`: 虚数误差函数
- `voigt`: Voigt 线型函数
- `w_of_z`: Faddeeva 函数
- `im_w_of_x`: Faddeeva 函数虚部

## 基本信息

- **软件**: libcerf
- **官网**: https://jugit.fz-juelich.de/mlz/libcerf
- **目标平台**: HarmonyOS/OpenHarmony aarch64
- **构建系统**: CMake
- **编译器**: Clang 15.0.4

## 可用版本

| 版本 | 状态 | 测试通过率 | 补丁数 |
|------|------|-----------|--------|
| 3.3 | success | 100% (18/18) | 0 |

## 编译指导

### 环境要求
- Clang 15.0.4 或兼容编译器
- CMake 4.1.2+
- HarmonyOS/OpenHarmony aarch64 系统

### 编译步骤
```bash
# 下载源码
wget https://jugit.fz-juelich.de/mlz/libcerf/-/archive/v3.3/libcerf-v3.3.tar.gz
tar xzf libcerf-v3.3.tar.gz
cd libcerf-v3.3

# 配置和编译
cmake -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
cmake --build build

# 测试
ctest --test-dir build

# 安装
cmake --install build
```

### 注意事项
1. CMake 会警告 "System is unknown to cmake"，但不影响编译
2. 编译时会有约 200+ 个 complex initialization extension warnings，这些警告不影响功能
3. 所有测试均通过，可以安全使用

## 补丁清单

版本 3.3 无需补丁，源码直接编译成功。

## 已知限制

1. **平台识别**: cmake 不识别 HarmonyOS 系统，会显示警告但不影响编译
2. **C99 扩展**: 源码使用 complex initialization 扩展语法，会产生编译警告
3. **pkg-config**: 安装后 pkg-config 可能提示 Name field occurs twice，不影响使用

## 功能验证

### 库文件验证
```bash
# 检查库文件
ls -l $HOME/usr/local/lib/libcerf*.so
file $HOME/usr/local/lib/libcerf.so
# 输出: ELF 64-bit LSB shared object, ARM aarch64

# 检查头文件
ls -l $HOME/usr/local/include/cerf.h
```

### 测试验证
```bash
# 运行测试套件
cd build && ctest
# 结果: 18/18 tests passed, 0 tests failed
```

## 使用示例

### C 接口
```c
#include <cerf.h>
#include <complex.h>

double complex z = 1.0 + 2.0*I;
double complex result = cerf(z);
```

### C++ 接口
```cpp
#include <cerf.hpp>
#include <complex>

std::complex<double> z(1.0, 2.0);
std::complex<double> result = cerf(z);
```

## 文档资源

- 官方文档: https://jugit.fz-juelich.de/mlz/libcerf/-/blob/master/README.md
- API 文档: 安装后查看 `share/man/man3/` 和 `share/doc/cerf/html/`
- 测试报告: `archives/l/libcerf/3.3/reports/test-report.md`
