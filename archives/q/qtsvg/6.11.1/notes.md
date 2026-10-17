# qtsvg 6.11.1 适配笔记

## 编译环境
- 构建系统: cmake（Qt6 SVG 模块）
- 编译日期: 2026-08-06
- 编译器: clang 15 (OHOS aarch64)
- 状态: published

## 编译步骤

```bash
# 1. init-build（官方源码包 qtsvg-everywhere-src-6.11.1.tar.xz）
python3 scripts/ohc-run.py init-build qtsvg 6.11.1 --url <源码包> --tar tar.xz

# 2. 生成 CMake 配方并验证
python3 scripts/ohc-run.py conan-verify qtsvg 6.11.1
# ✅ 配方验证通过: qtsvg 6.11.1（G0-G4 + L2/L4/L5 全 PASS）
```

配方要点：
- `QT_QMAKE_TARGET_MKSPEC=harmonyos-clang`，依赖 qtbase/6.11.1.1（DBus 版，保持依赖链单一版本）
- qtbase 为 cmake_find_mode "none"，需显式设 `Qt6_DIR` / `Qt6Svg_DIR` / `Qt6SvgWidgets_DIR`
- CMAKE_MODULE_PATH 指向 qtbase 安装的 `lib/cmake/Qt6/platforms`（提供 Platform/HarmonyOS.cmake，保证 SONAME 正确处理）
- OHOS ELF 签名（`_sign_installed_elfs`）：test_package 运行必需

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(Qt6)` 找不到 Qt6Svg | qtbase 用 cmake_find_mode "none"，CMAKE_PREFIX_PATH 不生效 | generate() 显式设 Qt6_DIR / Qt6Svg_DIR 缓存变量 |
| 2 | 插件 DT_NEEDED 是字面相对路径，运行时加载失败 | CMake 不识别 HarmonyOS 平台，未生成 SONAME | CMAKE_MODULE_PATH 指向 qtbase 的 platforms 目录（Platform/HarmonyOS.cmake） |
| 3 | tst_qicon_svg 报 "SVG support is not available" | 测试运行找不到 imageformats 插件 | 测试环境设 QT_PLUGIN_PATH 指向构建树 plugins/，LD_LIBRARY_PATH 加 qtbase lib |
| 4 | test_package 找不到 Qt6Svg 配置 | test_package 的 find_package 走 *DIR 缓存变量 | 显式设 Qt6_DIR / Qt6Svg_DIR / Qt6SvgWidgets_DIR |
| 5 | `add_library(dbus-1)` 重复目标冲突（依赖侧） | harmonybrew 的 DBus1Config.cmake 无 target 保护 | 依赖 qtbase/6.11.1.1 已内置受保护版本 |

## 源码修改

- 无源码补丁（purity 适配，仅配方层修改）。

## 依赖版本

- qtbase 6.11.1.1（DBus 版，本任务链一并适配）
- 构建期 FetchContent 无外部网络依赖

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify qtsvg 6.11.1
# ✅ 配方验证通过: qtsvg 6.11.1
# 上游测试: tst_qicon_svg / tst_qsvgcss / tst_qsvggenerator / tst_qsvgplugin / tst_qsvgrenderer 5/5 PASS
# test_package: test_qtsvg（QSvgRenderer 渲染校验）PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（qtbase/6.11.1.1 依赖、ELF 签名） |
| conandata.yml | 官方 Qt 镜像源（清华/中科大/腾讯/阿里/download.qt.io）+ SHA256 |
| test_package/ | 消费者测试（QSvgRenderer 渲染校验）+ MANIFEST.yml |

## 注意事项

- 本任务链依赖顺序：qtbase/6.11.1.1 → qtsvg/6.11.1 → flameshot/14.0.0。
- qtsvg 的 Qt6Svg_DIR 等缓存变量必须在 generate() 显式设置（cmake_find_mode "none" 依赖不产生 CMakeDeps 配置）。
