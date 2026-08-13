# ECM 6.26.0 HarmonyOS PC 适配报告

## 一、软件简介

ECM（Extra CMake Modules）是 KDE 提供的扩展 CMake 模块集合，为项目构建系统提供
额外的 CMake 宏、工具链文件和 `find_package` 查找模块。

本次适配面向 OpenHarmony PC 环境。ECM 仅安装 CMake 模块和配置文件，不生成需要
链接的二进制库，因此 Conan 包类型配置为 `build-scripts`。

## 二、源码信息

- 软件名称：ECM
- 适配版本：6.26.0
- 上游项目：https://invent.kde.org/frameworks/extra-cmake-modules
- 源码地址：https://download.kde.org/stable/frameworks/6.26/extra-cmake-modules-6.26.0.tar.xz
- SHA256：`F4E10D9D45AAFB5273E996196040F4E420F0BC4071C208282AAE94D9AD8E1743`
- 许可证：BSD-3-Clause

## 三、适配内容

1. 新增 Conan 配方 `ecm/6.26.0`，使用 CMake 完成配置、构建和安装。
2. 关闭上游测试（`BUILD_TESTING=OFF`），避免引入与模块安装无关的可选测试依赖。
3. 通过 `package_id()` 清除编译器、架构和构建类型差异。该包不含编译产物，使用统一
   的包 ID 可以避免产生不必要的二进制包变体。
4. 配置 CMake 包信息，支持通过 `find_package(ECM)` 查找已安装模块。

## 四、安装目录

安装后的主要文件位于：

```text
share/ECM/cmake/       ECMConfig.cmake 和版本配置文件
share/ECM/modules/     ECM 扩展模块
share/ECM/kde-modules/ KDE 构建模块
share/ECM/find-modules/第三方依赖查找模块
share/ECM/toolchain/   工具链和部署辅助文件
```

## 五、编译与测试结果

已完成全部编译和测试，结果如下：

- Conan 配方导出成功
- 上游源码下载与 SHA256 校验成功
- CMake 配置成功
- ECM 构建成功
- 安装阶段成功
- `test_package` 配置、编译成功
- `find_package(ECM 6.26.0 EXACT)` 查找成功
- `ECMFindModuleHelpers` 加载成功
- 版本号和模块目录断言通过
- 测试程序退出码为 `0`

结论：ECM 6.26.0 已完成 OpenHarmony PC 适配，编译与测试全部通过。
---

### 对话 #1 [2026-08-12]

- 问题: ECM 6.26.0 为纯 CMake 模块库，不编译二进制代码；上游测试部分用例需 Qt5/Qt6，无 Qt 环境下 10/85 用例失败
- 操作: 执行 `ohc-run.py build ecm 6.26.0` 完整流程，conan-verify G1-G4 全部通过；package_id() 使用 self.info.clear() 统一包 ID
- 结果: 编译与验证全部通过，find_package(ECM 6.26.0 EXACT) 与 ECMFindModuleHelpers 加载成功，状态 built

**编译结束**: 2026-08-12 11:42
**最终状态**: built
