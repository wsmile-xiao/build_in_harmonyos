# fann — OpenHarmony 编译记录

## 基本信息
- 软件: fann (Fast Artificial Neural Network Library)
- 主页: https://github.com/libfann/fann
- 许可证: LGPL-2.1-or-later
- 构建系统: CMake
- 目标平台: ohos-aarch64

## 已编译版本
- 2.2.0 (2026-06-26) — 状态: built

## 编译指导
- CMake 4.x 需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（源码 cmake_minimum_required(VERSION 2.8) 不兼容）
- src/CMakeLists.txt 显式使用 SHARED 关键字，需 patch 改为 STATIC（R26 静态链接要求）
- 无第三方依赖

## 补丁清单
- 2.2.0: `0001-src-CMakeLists.txt.patch` — 将 ADD_LIBRARY SHARED 改为 STATIC
