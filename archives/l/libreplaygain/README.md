# libreplaygain r475 — OpenHarmony 编译记录

## 基本信息
- **软件**: libreplaygain
- **版本**: r475
- **构建系统**: CMake
- **目标平台**: HarmonyOS aarch64
- **编译器**: clang 15.0.4
- **编译日期**: 2026-05-11

## 软件简介

libreplaygain 是音频 ReplayGain 标准的实现库。ReplayGain 是一种音量标准化技术，用于计算音频文件的响度信息，以便在播放时保持一致的音量水平。

### 功能特性
- 分析音频文件计算 ReplayGain 值
- 提供静态库和共享库两种形式
- 支持多种音频格式

## 编译指导

### 系统要求
- CMake 3.5 或更高版本
- C 编译器（clang/gcc）
- HarmonyOS/OpenHarmony aarch64 环境

### 编译步骤

```bash
# 1. 解压源码
tar xzf libreplaygain_r475.tar.gz
cd libreplaygain_r475

# 2. 应用补丁（如果需要）
patch -p1 < patches/0001-cmake-version.patch

# 3. 创建构建目录
mkdir build && cd build

# 4. 配置
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local

# 5. 编译
make -j$(nproc)

# 6. 安装
make install
```

### 编译选项
- `CMAKE_INSTALL_PREFIX`: 安装路径前缀，默认为 `/usr/local`

## 补丁清单

### 0001-cmake-version.patch
- **说明**: 更新 CMake 最小版本要求从 2.4 到 3.5
- **原因**: CMake 4.1.2 要求最小版本 3.5
- **影响**: 仅修改 CMakeLists.txt 第一行，不影响编译逻辑
- **适用版本**: r475

## 已知限制

1. **无测试套件**: 项目不包含自动化测试，需手动验证库文件
2. **编译警告**: 会出现 GNU folding constant 警告，这是编译器扩展行为，不影响功能

## 功能验证

### 验证库文件
```bash
# 检查静态库
ls -lh ~/usr/local/lib/libreplaygain.a

# 检查共享库
ls -lh ~/usr/local/lib/libreplaygain.so

# 查看符号
nm ~/usr/local/lib/libreplaygain.a | grep replaygain
```

### 预期输出
- `libreplaygain.a`: 静态库文件，约 11KB
- `libreplaygain.so`: 共享库文件，约 26KB
- 符号表中应包含 ReplayGain 相关函数

## 依赖关系

### 无外部依赖
libreplaygain 是独立的音频分析库，不依赖其他第三方库。

## 相关链接

- [ReplayGain 标准](https://wiki.hydrogenaud.io/index.php?title=ReplayGain)
- [libreplaygain 源码](https://www.musepack.net/)