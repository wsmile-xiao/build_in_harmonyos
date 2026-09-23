# 适配笔记 — qtserialport 6.8.2

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件名 | qtserialport |
| 版本 | 6.8.2 |
| 构建系统 | CMake |
| 上游仓库 | https://github.com/qt/qtserialport |
| 源码 URL | https://download.qt.io/official_releases/qt/6.8/6.8.2/submodules/qtserialport-everywhere-src-6.8.2.tar.xz |
| SHA256 | ed17e02361e989f149f58d021ab8cd66f21db4cdfb8cde0a462017e6ac1e3be7 |

## 依赖

| 依赖 | 版本 | 状态 |
|------|------|------|
| qtbase | 6.11.1 | 已发布 |

> qtbase/6.8.2 未发布到制品仓，使用 qtbase/6.11.1 作为构建依赖。
> CMake find_package(Qt6 6.8.2 ...) 接受 Qt6 6.11.1（版本兼容：6.11.1 >= 6.8.2）。

## 构建配置

- CMAKE_PREFIX_PATH: qtbase 包前缀
- CMAKE_MODULE_PATH: qtbase/lib/cmake/Qt6/platforms
- QT_QMAKE_TARGET_MKSPEC: harmonyos-clang
- BUILD_SHARED_LIBS: ON
- QT_BUILD_TESTS: ON
- QT_BUILD_EXAMPLES: OFF
- FEATURE_libudev: OFF
- CXX flags: -DQT_NO_ARM_AES_INTRINSICS

## 上游测试

| 测试 | 描述 | 状态 |
|------|------|------|
| tst_qserialport | QSerialPort 核心 API 测试 | 在 build() 中构建并运行 |
| tst_qserialportinfo | QSerialPortInfo 端口枚举/属性测试 | 在 build() 中构建并运行 |

## 适配说明

- 基于 qtserialport/6.11.1 的成功适配经验，适配 6.8.2 版本。
- 使用 qtbase/6.11.1 作为构建依赖（6.8.2 未发布到制品仓）。
- 构建、签名、测试流程与 6.11.1 版本一致。
---

**编译结束**: 2026-09-05 06:51
**最终状态**: built
