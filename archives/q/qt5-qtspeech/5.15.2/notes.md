# qt5-qtspeech 5.15.2 Build Notes

## Source
- Upstream tarball: qtspeech-everywhere-src-5.15.2.tar.xz (download.qt.io 官方源)
- sha256: c810fb9eecb08026434422a32e79269627f3bc2941be199e86ec410bdfe883f5（download.qt.io 官方源与清华镜像双源实测一致）

## Build System
- qmake (Qt5 addon module)
- Products: lib/libQt5TextToSpeech.so.5.15.2（src/tts）+ lib/cmake/Qt5TextToSpeech +
  mkspecs/modules/qt_lib_texttospeech*.pri + include/QtTextToSpeech
- 零源码修改适配（无补丁）；平台差异全部在配方层处理

## TTS Engine Plugins (platform backend exclusion)
上游 src/plugins/tts 按 configure.json 特性探测裁剪：
- speechdispatcher: 需要 speech-dispatcher 守护进程 + libspeechd（OHOS 无）
- flite: 需要 flite 合成器 + alsa（OHOS 无）
- sapi/winrt: windows；osx/ios: apple；android: android
→ OHOS 上 qmake 特性探测关闭 speechd/flite，src/plugins/tts 编译零插件
（本地原型实测 plugins/ 目录为空），libQt5TextToSpeech 本体完整：
readelf -d NEEDED 仅 libQt5Core.so.5 + libc++_shared.so + libc.so

## Dependency Resolution
- qt5-qtbase/5.15.2.2: qmake/moc 工具 + Qt5Core（libQt5TextToSpeech 唯一 Qt 依赖）
- 可写 Qt prefix（qt-prefix 模式，同 qtmultimedia/qtscxml 先例）：symlink 镜像
  qtbase 包目录 + 重写 mkspecs .pri 构建路径 + 自写 qt.conf

## Build Steps
1. 建可写 Qt prefix（qt-prefix 模式）
2. qmake -spec linux-clang qtspeech.pro
3. make -j4 QMAKE_STRIP=""（防 strip——OHOS 加载器拒绝被 strip 的 ELF）
4. tests/auto/texttospeech: qmake+make+run（binary-sign-tool 签名测试二进制后真跑）
5. tests/auto/cmake: cmake+ctest module_includes（三项环境适配，见下）
6. make install INSTALL_ROOT=<staging> 后搬入包目录
7. .prl/.la/.pc 陈旧构建路径改写为 package_folder

## Upstream Tests (real run, rule4)
- tests/auto/texttospeech 真跑（配方 build() 内，QT_QPA_PLATFORM=offscreen）：
  - Totals: 2 passed, 3 failed, 0 skipped, 2 blacklisted
  - 2 passed = initTestCase + cleanupTestCase（引擎无关的引导用例）
  - 3 failed（say_hello/pitch/volume）全部携带文档化签名
    "No text-to-speech plug-ins were found."（QSYSTEM 行）——OHOS 无 TTS 引擎
    环境限制非库缺陷；配方 _validate_engine_absence() 逐项校验失败集与签名，
    出现引擎无关失败立即 ConanException（防真实缺陷被误豁免）
  - 2 blacklisted（speech_rate/set_voice）为上游 BLACKLIST 文件 '*' 条目
    在全平台拉黑（非本平台特有）
- tests/auto/cmake 真跑（配方 build() 内直接驱动 ctest）：
  - 1/1 module_includes Passed, 4.26s（消费者模块包含性 + 链接验证）
  - 三项环境适配（本地原型实测缺一即挂）：
    1. CMAKE_POLICY_VERSION_MINIMUM=3.5（CMake 4.x 移除对上游模板
       cmake_minimum_required(2.8) 的兼容）
    2. <build>/b/mkspecs/linux-clang 符号链接：qt5-qtbase 包内
       Qt5CoreConfigExtrasMkspecDir.cmake 残留构建期路径
       "<prefix>/../b//mkspecs/linux-clang"，该链接使
       _qt5_Core_check_file_exists 通过
    3. CMAKE_SYSTEM_NAME=Linux 覆盖（与 test_package generate() 双覆盖）：
       Qt5 config/mkspecs 探测按 Linux 平台路径解析

## Issues Encountered
- 测试二进制/tst_qtexttospeech 未签名时 OHOS 加载器拒绝执行 →
  binary-sign-tool -selfSign 1 + chmod 755 后可运行
- 上游 cmake 套件的 make check 入口在 CMake 4.x 下直接报
  "Compatibility with CMake < 3.5 has been removed" → 直接驱动 cmake/ctest
  并注入 CMAKE_POLICY_VERSION_MINIMUM=3.5
- 构建宿主环境注入的 LD_LIBRARY_PATH 携带不兼容 libc++_shared.so 副本时会
  遮蔽系统版本——测试子进程环境确定性构造（源树 lib + qtbase 包 lib +
  toolchain lib + /system/lib64），不继承父级 LD_LIBRARY_PATH

---

**编译结束**: 2026-10-06
**最终状态**: built
