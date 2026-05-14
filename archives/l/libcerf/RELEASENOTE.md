# libcerf — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libcerf-3.3-ohos-aarch64.tar.gz -C ~/usr/local

cd libcerf-3.3-ohos-aarch64 && sh install-libcerf-3.3.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.3 | success | 0 |

## 当前版本 (3.3) 详情

### 包内容
- 库文件: lib/libcerf.so (74KB), lib/libcerfcpp.so (74KB)
- 头文件: include/cerf.h
- CMake 配置: lib/cmake/cerf/
- pkg-config: lib/pkgconfig/libcerf.pc
- 文档: share/man/man3/, share/doc/cerf/html/
- 包大小: 270KB (主包) + 51KB (debug 包)

### 编译信息
- 构建系统: cmake
- 编译器: clang 15.0.4
- 目标: HarmonyOS aarch64
- 质量门禁: PASS (G1-G4 全部通过)
- 补丁数: 0
- 测试结果: 18/18 全部通过 (100%)

### 功能说明
libcerf 提供复数误差函数的实现，包括：
- cerf: 复数误差函数
- cdawson: 复数 Dawson 积分
- erfcx: 缩放互补误差函数
- erfi: 误差函数虚部
- voigt: Voigt 线型函数
- w_of_z: Faddeeva 函数

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- Clang 15.0.4 或兼容编译器
