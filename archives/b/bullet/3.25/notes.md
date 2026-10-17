# bullet 3.25 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-05
- 编译器: clang/clang++ 15.0.4
- 状态: published

## 编译步骤

1. CMake 配置: cmake -DBUILD_CPU_DEMOS=OFF -DBUILD_OPENGL3_DEMOS=OFF -DBUILD_BULLET2_DEMOS=OFF -DBUILD_EXTRAS=OFF -DBUILD_UNIT_TESTS=OFF -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 ..
2. 编译: make -j4
3. 安装: make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置失败 | CMakeLists.txt 中 cmake_minimum_required(VERSION 2.4.3) 与 CMake 4.x 不兼容 | 通过补丁 0001-CMakeLists.txt.patch 将最低版本提升至 3.5 |
| 2 | CMake 不认识 HarmonyOS 平台 | CMake 没有 HarmonyOS platform module (E092) | 在 generate() 中设置 CMAKE_SYSTEM_NAME=Linux 和 CMAKE_SYSTEM_PROCESSOR=aarch64 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`: 将 `cmake_minimum_required(VERSION 2.4.3)` 提升至 `cmake_minimum_required(VERSION 3.5)`

## 依赖版本

无依赖。

## 验证结果

```bash
# test_package/test.cpp 物理模拟测试
# 创建动力学世界: 地面平面 + 下落球体
# 模拟 3 秒 (180 步, 1/60s per step)
# 验证球体静止在地面 (y ≈ 1.0, 半径=1)
PASS: sphere at y=1.00 (expected ~1.0)
```

## 注意事项

- bullet 编译为纯静态库 (11 个 .a 文件)
- CMAKE_SYSTEM_NAME=Linux 是 E092 问题的标准解决方案
- 链接顺序: BulletDynamics → BulletCollision → LinearMath

---

**编译结束**: 2026-08-05 12:38
**最终状态**: published
