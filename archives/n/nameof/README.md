# nameof 0.10.4 for HarmonyOS

## 概述

nameof 在 HarmonyOS/OpenHarmony (aarch64) 上的适配记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | nameof |
| 版本 | 0.10.4 |
| 下载地址 | https://github.com/Neargye/nameof/archive/refs/tags/v0.10.4.tar.gz |
| 官方仓库 | https://github.com/Neargye/nameof |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 架构 | aarch64-linux-ohos |
| 编译器 | clang (LLVM) |
| 构建系统 | CMake (INTERFACE header-only) |

## 编译步骤

```bash
# 1. 下载源码
wget https://github.com/Neargye/nameof/archive/refs/tags/v0.10.4.tar.gz
tar -xzf v0.10.4.tar.gz

# 2. 配置（header-only，无需编译）
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release

# 3. 验证可用
cmake --build build --target nameof  # INTERFACE 目标，无实际编译产物
```

## 遇到的问题

本次适配无编译期问题；header-only 库按 nlohmann-json 同型配方固化，无补丁。

## 测试结果

详见 [test-report.md](./reports/test-report.md)

| 测试项 | 结果 |
|--------|------|
| 上游单元测试（Catch2 单头文件） | ✅ |
| HarmonyOS 专项消费者测试 | ✅ |

## 经验总结

1. header-only INTERFACE 库配方：`package_type="header-library"`、`no_copy_source=True`、仅复制 include/ 与 LICENSE 到包内。
2. 上游测试依赖内嵌 Catch2 单头（test/3rdparty/Catch2/catch.hpp），不引入额外依赖。

## 参考资料

- https://github.com/Neargye/nameof
- https://github.com/Neargye/nameof/blob/v0.10.4/README.md