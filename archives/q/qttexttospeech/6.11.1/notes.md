# qttexttospeech 6.11.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-12
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `ohc-run.py init-build qttexttospeech 6.11.1 --url=https://mirrors.tuna.tsinghua.edu.cn/qt/official_releases/qt/6.11/6.11.1/submodules/qtspeech-everywhere-src-6.11.1.tar.xz`
2. CMake 配置（conan create 内部）：`QT_QMAKE_TARGET_MKSPEC=harmonyos-clang`、`Qt6_DIR=<qtbase 包>/lib/cmake/Qt6`、`Qt6Multimedia_DIR=<qtmultimedia 包>/lib/cmake/Qt6Multimedia`
3. `cmake --build` 生成 libQt6TextToSpeech.so（src/tts 模块）
4. `ctest` 运行上游 auto tests（tst_qtexttospeech/tst_qvoice，QT_QPA_PLATFORM=offscreen）2/2 通过
5. `conan-verify` 8 道门禁（G0-G4 + L2/L4/L5）全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 找不到 Qt6TextToSpeech 组件 | src/tts 模块 PUBLIC_LIBRARIES 含 Qt::Multimedia，缺 Qt6Multimedia_DIR 时 TextToSpeech 模块被跳过 | requirements 加 qtmultimedia/6.11.1；generate() 显式设 Qt6Multimedia_DIR（主包与 test_package） |
| 2 | CMakeToolchain 把 CMakeUserPresets.json 写回 source | 默认 user preset 行为 | E225：`cmake_layout(build_folder="$TMP")` + `user_presets_path=False` |
| 3 | test_package configure 找不到 Qt6TextToSpeech | Qt6TextToSpeechConfig.cmake 依赖 Qt6Multimedia（find_package REQUIRED） | test_package generate() 显式设 Qt6Multimedia_DIR |
| 4 | ctest 运行报 `Could not find the Qt platform plugin "xcb"` | tst_qtexttospeech/tst_qvoice 构造 QGuiApplication，OHOS 无 xcb | build() 注入 `QT_QPA_PLATFORM=offscreen` |
| 5 | package() SBOM 装配失败：`Could not find external SBOM document sbom/qtmultimedia-6.11.1.spdx` | Qt 6.11 SBOM 装配在 install 阶段查找依赖模块 spdx，qtmultimedia 包 spdx 位于 p/sbom/ 而装配脚本仅在 lib/cmake 等路径搜索 | generate() 设 `QT_GENERATE_SBOM=False`（E324） |
| 6 | test_package.cpp Qt 6.11 API 编译错误 | Qt 6.11 无 `engines()`/`QLocale::isEmpty()`；Q_OBJECT 类需 AUTOMOC | 改用 Qt 6 API；CMakeLists 加 `CMAKE_AUTOMOC ON`；恒真断言改为连接建立断言 + INFO 诊断 |

## 源码修改

无补丁（0 个）：qttexttospeech 适配全部在配方层完成（依赖声明、CMakeToolchain 变量、ctest 环境注入），无需修改上游源码。

## 依赖版本

- qtbase/6.11.1（Core/Gui 等基础模块 + harmonyos-clang mkspec）
- qtmultimedia/6.11.1（src/tts PUBLIC_LIBRARIES Qt::Multimedia 必需）

## 验证结果

```bash
# ctest（build() 内，QT_QPA_PLATFORM=offscreen）
tst_qtexttospeech ............... Passed
tst_qvoice ...................... Passed
# test_package 消费者测试
qttexttospeech consumer test: ALL PASSED
# conan-verify
G0-G4 全 PASS，可标记 status: published
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | Conan 配方（CMake + qtbase/qtmultimedia 依赖） |
| test_package/ | 消费者测试（QTextToSpeech API 6 条断言 + 2 项 INFO 诊断） |
| reports/ | conan-verify-report.md、test-report.md |
| knowledge/drafts/E324 | SBOM 外部引用 spdx 找不到的错误模式草稿 |

## 注意事项

- qttexttospeech 依赖 qtmultimedia（src/tts 的 PUBLIC_LIBRARIES 硬引用 Qt::Multimedia target），发布顺序必须先 qtmultimedia 后 qttexttospeech。
- OHOS 无 TTS 引擎后端，`availableVoices()` 返回空、`stateChanged` 不触发属预期，test_package 以 INFO 诊断说明而非伪造断言。
- 无 xcb 平台插件，上游测试运行需 `QT_QPA_PLATFORM=offscreen`。

---

**编译结束**: 2026-08-13 09:33
**最终状态**: published
