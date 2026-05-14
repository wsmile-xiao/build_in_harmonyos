# libcerf 3.3 — OpenHarmony 编译记录

## 基本信息

- **软件**: libcerf
- **版本**: 3.3
- **构建系统**: CMake
- **编译器**: Clang 15.0.4
- **目标平台**: HarmonyOS/OpenHarmony aarch64
- **源码地址**: https://jugit.fz-juelich.de/mlz/libcerf/-/archive/v3.3/libcerf-v3.3.tar.gz
- **编译日期**: 2026-04-28
- **状态**: ✅ success

## 编译产物

### 库文件
- `lib/libcerf.so` (74KB) - C 接口共享库
- `lib/libcerfcpp.so` (74KB) - C++ 接口共享库

### 头文件
- `include/cerf.h` (3.4KB) - C/C++ 接口头文件

### 配置文件
- `lib/pkgconfig/libcerf.pc` - pkg-config 配置
- `lib/cmake/cerf/*.cmake` - CMake 配置文件

### 文档
- `share/man/man3/*.3` - man 手册页 (15 个)
- `share/doc/cerf/html/*.html` - HTML 文档 (15 个)

## 编译指导

### 配置命令
```bash
cmake -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
```

### 编译命令
```bash
cmake --build build -j$(nproc)
```

### 安装命令
```bash
# Staging 安装 (打包用)
DESTDIR=$HOME/test-install-libcerf-3.3 cmake --install build

# 本地安装 (验证用)
cmake --install build
```

### 编译注意事项

1. **系统识别警告**: CMake 会提示 "System is unknown to cmake, create: Platform/HarmonyOS"，但不影响编译
2. **complex initialization warnings**: 源码使用 C99 complex 扩展语法，会产生约 200+ 个编译警告，这些警告不影响功能
3. **无补丁**: 源码直接编译成功，无需任何修改

## 补丁清单

本版本无补丁。源码直接编译成功。

patches/ 目录为空。

## 测试结果

### 测试统计
- **测试命令**: `ctest --test-dir build`
- **总测试数**: 18
- **通过**: 18
- **失败**: 0
- **跳过**: 0
- **通过率**: 100%
- **耗时**: 0.61 秒

### 测试覆盖

**C 接口测试** (9 个):
- cerftest_c - 复数误差函数
- dawsontest_c - Dawson 积分
- erfcxtest_c - 缩放互补误差函数
- imwofxtest_c - Faddeeva 函数虚部
- realtest_c - 实数函数
- statusquotest_c - 状态商
- voigttest_c - Voigt 线型
- widthtest_c - 宽度计算
- wofztest_c - Faddeeva 函数

**C++ 接口测试** (9 个):
- cerftest_cpp, dawsontest_cpp, erfcxtest_cpp, imwofxtest_cpp, realtest_cpp, statusquotest_cpp, voigttest_cpp, widthtest_cpp, wofztest_cpp

详细测试报告: `reports/test-report.md`

## 质量门禁

- **G1 二进制完整性**: ✅ PASS
- **G2 功能可用性**: ✅ PASS
- **G3 可移植性**: ✅ PASS
- **G4 档案完整性**: ✅ PASS

详细质量报告: `reports/quality-report.md`

## 已知限制

1. **cmake 平台识别**: cmake 不识别 HarmonyOS 系统，会产生警告但不影响编译和运行
2. **C99 complex 扩展**: 源码使用 complex initialization 扩展语法，编译器会产生扩展警告
3. **pkg-config 配置**: 安装后的 .pc 文件可能有重复的 Name field，不影响实际使用

## 功能验证

### 库文件验证
```bash
file $HOME/usr/local/lib/libcerf.so
# 输出: ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV), dynamically linked

file $HOME/usr/local/lib/libcerfcpp.so
# 输出: ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV), dynamically linked
```

### API 验证
库提供以下 API:
- `cerf`, `cerfc` - 复数误差函数
- `cdawson` - 复数 Dawson 积分
- `erfcx`, `cerfcx` - 缩放互补误差函数
- `erfi`, `cerfi` - 虚数误差函数
- `voigt`, `voigt_hwhm` - Voigt 线型函数
- `w_of_z`, `im_w_of_z` - Faddeeva 函数

## 归档文件

- `packaging/libcerf-3.3-ohos-aarch64.tar.gz` (270KB) - 主预编译包
- `packaging/libcerf-3.3-ohos-aarch64-debug.tar.gz` (51KB) - 调试符号包
- `packaging/install-libcerf-3.3.sh` (1.3KB) - 安装脚本

## 知识沉淀

本次编译发现的经验:
1. cmake 在未知平台（HarmonyOS）上可以正常工作，仅需忽略系统识别警告
2. complex initialization 扩展警告不影响数学库的实际计算精度和稳定性
3. libcerf 的测试套件完整，覆盖率高，适合作为数值计算库的基础依赖
