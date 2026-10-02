# qzxing

QZXing barcode/QR code scanner library — C++/Qt port of the ZXing library.

- 上游: https://github.com/ftylitak/qzxing
- 许可证: Apache-2.0
- 构建系统: CMake（上游 src/CMakeLists.txt + 1 个 OHOS 适配补丁）
- 依赖: qt5-qtbase（Qt5Core/Qt5Gui/Qt5Concurrent）

## Key adaptations for OHOS
- 共享库交付：VERSION 3.3.0 / SOVERSION 3（SONAME libqzxing.so.3），
  QZXING_LIBRARY 私有导出宏，移除 PUBLIC DISABLE_LIBRARY_FEATURES
- cmake_minimum_required 3.3→3.10（CMake 4 policy）；Qt5 消费走
  find_package(qt5-qtbase) 的 CMakeDeps 根 config（其中声明 Qt5::Core/
  Qt5::Gui/Qt5::Concurrent 组件 target，conan 2 CMakeDeps 不生成按模块的
  Qt5Core-config.cmake，原生 Qt5Config.cmake 伞形 config 又不可重定位），
  QML 三模块移入 QZXING_USE_QML 守卫、Multimedia 移入 QZXING_MULTIMEDIA
  守卫（核心构建不强制 Svg/Quick/QuickControls2/Multimedia）
- NO_ICONV 对齐上游 Android/.pri 路径，规避 OHOS musl iconv 原型分叉
- 显式 moc（QZXing.h/ImageHandler.h）：AUTOMOC 在无 QT_VERSION_MAJOR 时
  检测不到 Qt5，共享库缺 metaobject 会在加载期炸；moc 路径由配方经
  QZXING_MOC_PATH 指向 qt5-qtbase bin/moc
- 解码器注册：MultiFormatReader.cpp 的注册被 ENABLE_DECODER_* 宏门控，
  上游 CMakeLists 只在 QZXING_USE_DECODER_* 选项 ON 时才定义（默认全关
  =打包库零解码器，真机实证）；配方在 generate() 全开 5 个解码器选项，
  与 .pro 无条件全开对齐
- 上游测试（46 编码单元方法 + 1110 次解码尝试的 PNG 语料）经生成式 CMake
  harness 在真机执行并解析 stdout 验证：解码健康签名与上游自己提交的参考
  日志 12/17 格式逐字一致（含 0002 修正上游 testEncode 坏夹具，见 notes.md）
