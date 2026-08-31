# libngf-qt 0.3.1 适配笔记

## 编译环境
- 构建系统: qmake (custom)
- 编译日期: 2026-08-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 使用 qt5-qtbase/5.15.2.2 提供的 qmake 构建
qmake -spec linux-clang project.pro
make -j4
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Project ERROR: Unknown module(s) in QT: quick` | declarative/ 子项目需要 Qt Quick (qt5-declarative)，制品仓中无此包 | 创建补丁 0001-conditional-quick-module.patch，使用 qtHaveModule(quick) 条件构建 |
| 2 | test_package CMake find_package(qt5-qtbase) 失败 | qt5-qtbase 使用组件级 cmake_file_name (Qt5Core/Qt5DBus)，无包级 qt5-qtbaseConfig | 改用 find_package(Qt5 CONFIG REQUIRED) 并直接依赖 qt5-qtbase |
| 3 | test.cpp `isValid()` 编译错误 | 0.3.1 版本 Ngf::Client 无 isValid() 方法 | 改用 isConnected() |
| 4 | 运行时找不到 libngf-qt5.so | test() 未将被测包 lib 目录加入 LD_LIBRARY_PATH | 添加 tested package lib dir 到 LD_LIBRARY_PATH |
| 5 | package() 从错误目录复制 .so | 源码结构中 .so 在 src/ 而非 lib/ | 修改 package() 从 src/ 目录复制 |
| 6 | package_info libs 名为 ngf-qt | 实际库名为 ngf-qt5 (Qt5 后缀) | 修改为 ngf-qt5 |
| 7 | package_info 缺少 Qt5DBus 依赖 | 库实际使用 QT += core dbus | 添加 qt5-qtbase::Qt5DBus 到 requires |

## 源码修改

1. `patches/0001-conditional-quick-module.patch` — 条件化构建 declarative 和 ut_declarativengfevent

## 依赖版本

- qt5-qtbase/5.15.2.2 (提供 Qt5Core, Qt5DBus, qmake)
- dbus/1.14.10 (qt5-qtbase 依赖)
- expat/2.8.2 (dbus 依赖)
- zlib/1.3.1 (qt5-qtbase 依赖)

## 验证结果

```bash
# conan-verify 全部通过
G1: PASS, G2: PASS, G3: PASS, G4: PASS
L2: PASS, L4: PASS, L5: PASS
# 本地 CI 模拟通过
setup.sh: PASS, build_and_test.sh: PASS
```

## 注意事项

- Qt Quick (qt5-declarative) 不可用时，declarative QML 插件和对应测试被条件跳过
- 核心库 libngf-qt5.so 完整构建，功能不受影响
- 当 Qt Quick 包发布后，补丁会自动启用完整构建

---

**编译结束**: 2026-08-19 06:10
**最终状态**: built
