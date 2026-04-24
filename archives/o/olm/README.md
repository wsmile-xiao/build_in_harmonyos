# olm — OpenHarmony 预编译包

## 软件简介

olm 是 Matrix 协议的加密库，实现了 Megolm 和 Olm 加密算法。该库为 Matrix 客户端提供端到端加密支持，是 Matrix 生态系统的核心加密组件。

**⚠️ 重要提示**: 该软件已标记为弃用状态，仅保留编译记录供参考。

### 软件特性
- **加密算法**: Olm (双棘轮算法) 和 Megolm (群组加密)
- **用途**: Matrix 端到端加密通信
- **源码**: https://gitlab.matrix.org/matrix-org/olm/
- **许可证**: Apache 2.0

## 构建系统
- **构建系统**: CMake
- **目标平台**: ohos-aarch64
- **编译状态**: partial（部分成功）

## 编译指导

### 环境要求
- HarmonyOS/OpenHarmony aarch64 SDK
- CMake >= 3.10
- C++ 编译器（支持 C++11）

### 构建命令
```bash
# 配置
cmake -H. -Bbuild \
  -DCMAKE_TOOLCHAIN_FILE=$OHOS_SDK/native/build/cmake/ohos.toolchain.cmake \
  -DOHOS_ARCH=arm64-v8a \
  -DCMAKE_BUILD_TYPE=Release

# 编译
cmake --build build

# 安装
cmake --install build --prefix $TEST_PREFIX
```

## 已知限制
- ⚠️ 软件已弃用，仅保留编译记录
- 功能测试有限，生产环境请谨慎使用

## 版本列表

| 版本 | 状态 | 补丁数 | 编译日期 |
|------|------|--------|----------|
| 3.2.16 | partial | 0 | 2026-04-24 |
