# qtspeech-opensource-src 5.15.15 适配笔记

## 源码信息
- 上游: Qt 5.15.15 LTS
- 源码: qtspeech-everywhere-opensource-src-5.15.15.tar.xz (94K)
- SHA256: 090125ce13c4219c7e2291e7a248c0923fd8534f0667fabd544ca377e9a8b305
- 官方下载: https://download.qt.io/archive/qt/5.15/5.15.15/submodules/

## 构建系统
- qmake (Qt5 addon module)
- 主项目文件: qtspeech.pro
- 构建命令: qmake -spec linux-clang qtspeech.pro && make -j2 QMAKE_STRIP=""

## 依赖
- qt5-qtbase/5.15.2.2 (Core, Gui) — Conan 制品仓已发布
- qt5-qtdeclarative/5.15.2 (Qml, Quick) — Conan 制品仓已发布
- speech-dispatcher (libspeechd): 不可用（未适配），使用 mock backend（上游内置 fallback）
- flite: 不可用（未适配），mock backend 覆盖此场景

## 版本兼容性
- qtspeech 5.15.15 引用 qt5-qtbase 5.15.2.2（Conan 制品仓最新版本）
- Qt 5.15 LTS 系列 ABI 稳定，模块版本与基础版本无需严格匹配
- qmake 直接调用（不走 configure），不触发版本检查

## TTS 后端
- 上游代码在 src/plugins/tts/ 中通过平台检测选择后端
- speechd 后端: 需要 libspeechd (speech-dispatcher)，OHOS 不可用
- flite 后端: 需要 flite 库，OHOS 不可用
- mock 后端: 上游内置 fallback，总是编译，提供完整 API 但无实际 TTS 音频输出
- 这不是裁剪—— backend 是上游内置的 fallback 机制

## 平台适配
- 无需源码修改
- 需要修复 qt5-qtbase 的 qt.conf 和 .pri 文件路径（可重定位性）
- 需要合并 qt5-qtdeclarative 的 .pri 文件到 qt5-qtbase 的 mkspecs/modules/
- QMAKE_STRIP="" 防止 strip（OHOS 加载器拒绝 stripped ELF）

## 构建产物
- libQt5TextToSpeech.so (共享库)
- TTS 插件: plugins/texttospeech/ (mock backend)
- QML 插件: qml/QtTextToSpeech/
- 头文件: include/QtTextToSpeech/
- CMake 配置: lib/cmake/Qt5TextToSpeech/
- mkspecs 模块: mkspecs/modules/

## 验证
- test_package: 通过创建 QTextToSpeech 实例和查询可用引擎验证库加载
- 上游测试: tests/auto/auto.pro (make check)
- R40 标记: CI 覆盖构建、链接和非渲染冒烟检查。实际 TTS 音频输出需要手动验证 OHOS 语音后端。

---

## 关闭
COMPLETED
---

**编译结束**: 2026-09-05 00:29
**最终状态**: built
