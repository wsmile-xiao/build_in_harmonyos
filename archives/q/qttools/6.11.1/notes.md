# qttools 6.11.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: built

## 关联 Issue
- qttools: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/957
- 主库 qttranslations: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/951
- qtbase PR: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/2889

## 依赖项
- qtbase 6.11.1 (已编译安装，Issue: #958)

## 源码信息

- URL: https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qttools-everywhere-src-6.11.1.tar.xz
- SHA256: 8e61835a679c93fa9c6065b142353c2071ba68e297898937c32a03777fcaf50d
- 格式: tar.xz

## 编译步骤

1. 初始化编译环境:
   ```bash
   ohc-run.py init-build qttools 6.11.1 --url=https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qttools-everywhere-src-6.11.1.tar.xz
   ```

2. CMake 配置（使用已安装的 qtbase）:
   ```bash
   cmake -DCMAKE_PREFIX_PATH=$HOME/usr/local \
         -DCMAKE_BUILD_TYPE=Release \
         -DQT_QMAKE_TARGET_MKSPEC=harmonyos-clang \
         -DQT_FEATURE_assistant=OFF \
         -DQT_FEATURE_designer=OFF \
         -DQT_FEATURE_pixeltool=OFF \
         -DQT_FEATURE_qdbus=OFF \
         -DQT_FEATURE_qdiag=OFF \
         -DQT_FEATURE_qplugininfo=OFF \
         ..
   ```

3. 编译:
   ```bash
   cmake --build . --parallel 2
   ```

4. 安装:
   ```
   cmake --install .
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 完整 qttools 会引入不需要的 GUI 工具 | qttranslations 仅依赖 Linguist 工具链 | 关闭 Assistant、Designer、PixelTool、qdbus、qdiag 和 qplugininfo |
| 2 | qttranslations 找不到 Linguist CMake 模块 | Qt Linguist 工具和 CMake 配置尚未安装 | 安装 qttools 后确认 Qt6LinguistTools 和 lrelease 位于 `$HOME/usr/local` |
| 3 | Conan 生成的 Qt6Config 缺少 Qt 原生组件 | CMakeDeps 无法重建 Qt6::Core、Qt6::BuildInternals 等上游配置 | 直接使用 qtbase 包内安装的 Qt6Config.cmake，并禁止为 qttools 生成同名空配置 |

## 验证结果

- CMake 配置：通过
- Qt Linguist 最小工具链编译：通过
- 安装到 `$HOME/usr/local`：通过
- 工具存在性检查：7/7（100%）
- TS → QM（lrelease）：通过
- QM → TS（lconvert）：通过
- 源码翻译提取（lupdate）：通过
- 功能验证：3/3（100%）
- 下游 qttranslations 291 个 TS 生成 304 个 QM：通过
- 下游 qttranslations 完整 Conan create 与 conan-verify：通过
- Qt 上游测试套件：未执行，因此不声明上游测试通过率

已安装并检查的工具：

- lrelease
- lupdate
- lconvert
- lcheck
- lrelease-pro
- lupdate-pro
- ltext2id

## 注意事项

- qttools 提供 lrelease/lupdate/lconvert 工具，是 qttranslations 的必需依赖
- 手工构建时需确保 CMAKE_PREFIX_PATH 指向 qtbase 安装目录（如 `$HOME/usr/local`）
- 本次只适配 qttranslations 所需的 Linguist 工具链，不验证 Qt Designer、Assistant 等 GUI 工具
- Conan 配方从 `qtbase/6.11.1` 包目录加载 Qt6 和 Qt6BuildInternals 原生 CMake 配置
- test_package 同时验证 Qt6LinguistTools CMake 模块、qt_add_lrelease 命令和 lrelease 的 TS → QM 转换
