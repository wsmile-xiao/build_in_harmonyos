# libaec 1.1.6 — OpenHarmony 编译记录

## 基本信息
- 软件: libaec
- 版本: 1.1.6
- 描述: Adaptive Entropy Coding implementing Golomb-Rice algorithm
- 构建系统: CMake
- 目标: ohos-aarch64
- 源码 URL: https://gitlab.dkrz.de/k202009/libaec/-/archive/v1.1.6/libaec-v1.1.6.tar.bz2

## 编译指导

### 配置命令
```bash
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
```

### 编译命令
```bash
cmake --build build -j$(nproc)
```

### 安装命令
```bash
cmake --install build --prefix $HOME/usr/local
```

### 测试命令
```bash
ctest --test-dir build --output-on-failure
```

## 补丁清单
无补丁 - 编译无需修改源码

## 已知限制
- CMake 会显示 "System is unknown to cmake" 警告（HarmonyOS），但不影响编译
- libaec 是纯库软件，没有可执行命令行工具

## 功能验证
```bash
# 测试结果: 6/6 通过 (100%)
ctest --test-dir build
# 输出:
# check_code_options     Passed   40.06 sec
# check_buffer_sizes     Passed    0.03 sec
# check_seeking          Passed    0.36 sec
# check_long_fs          Passed    0.04 sec
# check_szcomp           Passed    0.13 sec
# check_rsi_block_access Passed   37.03 sec
```

## 安装产物
- `libaec.so` / `libaec.a` - 主库（自适应熵编码）
- `libsz.so` / `libsz.a` - SZ 兼容库
- `libaec.h` / `szlib.h` - 头文件
- cmake config files - 用于 CMake 项目集成

## 依赖
无外部依赖