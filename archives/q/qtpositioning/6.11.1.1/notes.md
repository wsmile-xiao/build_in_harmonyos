# qtpositioning 6.11.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-13
- 编译器: clang/clang++
- 平台: OHOS（OpenHarmony PC, aarch64）
- 状态: built

## 版本说明（6.11.1 → 6.11.1.1）

制品仓中已存在 qtpositioning/6.11.1（积分赛版），该版本配方**仅依赖 qtbase**，
源码 `src/CMakeLists.txt` 中 `if(TARGET Qt::Quick) add_subdirectory(positioningquick)`
因无 Qt::Quick 而跳过 positioningquick 子模块，发布包内**不含**
Qt6PositioningQuickConfig.cmake / libQt6PositioningQuick.so。

qtlocation 上游 CMakeLists 以 `assertTargets(... PositioningQuick ...)` 硬性检查
`Qt::PositioningQuick`，目标缺失时**跳过整个构建**（空包）→ test_package
`find_package(Qt6 COMPONENTS Location)` 失败 → qtlocation PR #4816 CI 失败
（构建 #23069，2026-08-13）。

修复：递增版本为 6.11.1.1，配方补 `qtdeclarative/6.11.1` 依赖 +
`QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 指向 qtdeclarative，使 positioningquick
子模块被构建并打包；package_info 增补 positioningquick 组件。

## 编译步骤

```bash
# 下载源码（中科大镜像已验证可用）
wget https://mirrors.ustc.edu.cn/qtproject/official_releases/qt/6.11/6.11.1/submodules/qtpositioning-everywhere-src-6.11.1.tar.xz

# Conan 构建
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Qt6 子模块源码下载 | 官方 download.qt.io 慢/不稳定 | conandata.yml 配置清华/中科大/腾讯/阿里镜像 fallback |
| 2 | OHOS 平台识别 | Qt CMake 默认不认识 HarmonyOS | QT_QMAKE_TARGET_MKSPEC=harmonyos-clang（参照 qtbase/6.11.1） |
| 3 | positioningquick 未构建 | 配方仅依赖 qtbase，无 Qt::Quick | 补 qtdeclarative/6.11.1 依赖 + QT_ADDITIONAL_PACKAGES_PREFIX_PATH |
| 4 | qtlocation 空包 | Qt::PositioningQuick 缺失 → assertTargets 跳过构建 | 本版本发布含 positioningquick 的 qtpositioning，qtlocation 依赖改为 6.11.1.1 |

## 注意事项
- qtpositioning 是依赖类包，必须先构建 qtbase/6.11.1 与 qtdeclarative/6.11.1
- 制品仓不支持同版本多 revision（409 Conflict），配方修复必须递增版本号后缀
