# dfc 3.1.1 for HarmonyOS

## 概述

dfc 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | dfc |
| 版本 | 3.1.1 |
| 官方仓库 | https://github.com/rolinh/dfc |
| 许可证 | BSD-3-Clause |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) / musl-gcc |
| 构建系统 | CMake |

## 编译步骤

```bash
# 1. 下载源码
wget https://github.com/rolinh/dfc/archive/v3.1.1.tar.gz
tar -xzf dfc-3.1.1.tar.gz
cd dfc-3.1.1

# 2. 应用补丁
patch -p1 < patches/0001-harmonyos-platform-support.patch

# 3. 创建构建目录
mkdir build && cd build

# 4. 配置
cmake .. -DCMAKE_BUILD_TYPE=RELEASE -DNLS_ENABLED=false

# 5. 编译
make -j$(nproc)

# 6. 安装
make install PREFIX=$HOME/usr/local
```

## 补丁说明

详见 [patches/0001-harmonyos-platform-support.patch](./patches/0001-harmonyos-platform-support.patch)

**修改文件**:
- `CMakeLists.txt`: 添加 HarmonyOS 系统检测
- `src/platform/services-linux.c`: 改进 mtab 文件路径查找

## 测试结果

详见 [test-reports/dfc-test-report.md](./test-reports/dfc-test-report.md)

| 测试项 | 结果 |
|--------|------|
| 基本运行 | ✅ PASS |
| 显示文件系统类型 | ✅ PASS |
| JSON 导出 | ✅ PASS |
| CSV 导出 | ✅ PASS |
| inode 信息 | ✅ PASS |
| HarmonyOS 文件系统支持 | ✅ PASS |

**通过率**: 100% (6/6)

## 预编译包

- `prebuilt/dfc-aarch64-harmonyos`: 82KB (完整版)
- `prebuilt/dfc-aarch64-harmonyos-stripped`: 74KB (精简版)