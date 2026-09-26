# libkmahjongg 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `init-build libkmahjongg 26.04.0 --url=https://download.kde.org/stable/release-service/26.04.0/src/libkmahjongg-26.04.0.tar.xz`
   - 注意：Savannah 镜像 URL (download.savannah.nongnu.org) 404，改用 KDE 官方 download.kde.org
2. `lang-preflight` — 判定 cpp（CMakeLists.txt project + 源文件主体 100% C++）
3. `conan-init` 生成骨架后，手工改写为 CMake 配方（自动生成误判 autotools）
4. `conan-verify` — 多轮修复后 G1-G4 全部 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 找不到 ECM | 未声明 ecm tool_require | build_requirements 添加 ecm/6.20.0，generate() 手动设置 ECM_MODULE_PATH |
| 2 | 找不到 Qt6Svg | qtsvg 是 cmake_find_mode=none，Qt6Config 在其 prefix 内找不到 Svg 组件 | generate() 显式设置 Qt6Svg_DIR = qtsvg 包 lib/cmake/Qt6Svg |
| 3 | test_package 链接后运行时 libKMahjongg6.so.6 找不到 | KF6 依赖 libs 的 DT_NEEDED 含构建期相对路径 | test() 在 <build>/../../bin 建符号链接农场（同 ktextwidgets 模式） |
| 4 | 运行时 "Permission denied" 加载 .so | OHOS loader 校验 ELF 签名，本地构建的 .so 无有效 codesign | conanfile package() 中调用 binary-sign-tool 签名已安装 ELF |
| 5 | 本地缓存 KF6/Qt6 依赖包被 conan create --build=missing 重编译后无签名 | 依赖配方未内嵌签名步骤 | 对 ~/.conan2/p 下相关 .so 重新 binary-sign-tool 签名（CI 环境已有签名，仅本地缓存需处理） |
| 6 | qtpaths 运行失败导致 configure 失败 | qtbase 本地重编译产物缺签名 | 重新签名 libQt6Core.so.6.11.1 后恢复 |

## 依赖版本

- qtbase/6.11.1 (Qt6 Core/Gui/Widgets)
- qtsvg/6.11.1 (Qt6Svg)
- kconfig/6.14.0, kconfigwidgets/6.14.0, kcoreaddons/6.14.0
- kwidgetsaddons/6.14.0, ki18n/6.14.0
- ecm/6.20.0 (tool_requires)

## 验证结果

```
conan-verify libkmahjongg 26.04.0
  G1 配方完整性: PASS
  G0 预构建风险评估: PASS
  G2 conan create: PASS（libKMahjongg6.so.6 构建 + test_package 链接通过）
  G3 系统同名库隔离: PASS
  G4 产物完整性: PASS
```

test_package 运行验证（R34 真实 API 校验，非空壳）：
- `KMahjonggTileset::loadDefault()` 真实加载默认 tileset 并校验返回结果，
  加载失败返回非 0 退出码使测试失败（评审意见闭环：test.cpp 由"无条件 PASS"
  改为真实加载校验）
- 通过：`PASS: KMahjonggTileset default tileset loaded OK`

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（含 ELF 签名步骤） |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | consumer 测试（KMahjonggTileset 真实 loadDefault 加载校验） |

## 注意事项

- 本包为库类型，无需 commands.json
- 产物 libKMahjongg6.so.6 输出到 lib/，头文件到 include/KMahjongg6/
- CI 环境依赖包均有 CI 签名；本地缓存重编译的依赖需注意签名问题（E537 相关）
---

**编译结束**: 2026-09-15 01:20
**最终状态**: built
