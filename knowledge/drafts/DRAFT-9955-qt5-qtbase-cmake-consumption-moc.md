# DRAFT-9955 — qt5-qtbase 消费方库在 OHOS conan 环境的 CMake 集成三坑

- **条目 ID**: `DRAFT-9955-qt5-qtbase-cmake-consumption-moc`
- **严重度**: 3（🔴 严重——按默认 CMake 打包的库消费侧功能全灭）
- **类别**: cmake, conan, dependency, linking, relocatable, ohos
- **触发工具/阶段**: cmake | conan | CMakeDeps | AUTOMOC — configuration / build / testing / runtime
- **来源**: qzxing 3.3.0 适配（feat/qzxing-3.3.0，OHOS PC aarch64 真机，2026-09-30）

## 错误特征

```
Could not find a package configuration file provided by "Qt5Core"
imported target "Qt5::Core" references the file .../b//mkspecs/linux-clang
    ... but this file does not exist
AUTOMOC ... disabled (dev warning) —— 构建"成功"，加载期
    undefined symbol: QZXing::staticMetaObject
打包库消费侧 decodeImage 全部失败（MultiFormatReader 零注册解码器）
```

## 场景

依赖 qt5-qtbase/5.15.2（Qt5 系）的三方库以 CMake 构建并交付 conan 包
（qzxing 3.3.0 为实例，含 Q_OBJECT 类、上游 src/CMakeLists.txt 原生支持
Qt5）。四个坑全部"链接成功、运行期才爆"，任何单点都不在 configure 阶段报错。

## 根因（四层）

1. **conan 2 CMakeDeps 不生成按模块 config**：cmakedeps 模板对组件只输出
   根 config（qt5-qtbase-config.cmake）+ 共享 Targets 文件，模板代码中
   组件级 `cmake_file_name` 零引用（conan 2.29 模板源码实测）——不存在
   Qt5Core-config.cmake / Qt5Gui-config.cmake，`find_package(Qt5Core)`
   必败。唯一可用入口是 `find_package(qt5-qtbase)` 根 config：它声明全部
   Qt5::Core/Qt5::Gui/Qt5::Concurrent 等组件 target（组件 cmake_target_name
   即 Qt5::*，链接行不变）。
2. **原生 Qt5Config.cmake 伞形 config 不可重定位**：Qt5CoreConfig.cmake
   引用构建机路径 `$PREFIX/../b//mkspecs/linux-clang`，二进制包在消费者
   机器没有该构建目录，configure 直接失败。注意 Qt6 的伞形 config **可**
   重定位（qscintilla2 的 Qt6_DIR 范式），Qt5 不可，勿混用。
3. **AUTOMOC 靠 QT_VERSION_MAJOR 判定 Qt 版本**：conan CMakeDeps 不设
   QT_VERSION_MAJOR，CMake 检测不到 Qt5 便静默禁用 AUTOMOC。共享库默认
   允许未定义符号，无 metaobject 的库照样链接成功，QZXing::staticMetaObject
   留空在**加载期**才炸。修复: 显式 moc（QZXing.h/ImageHandler.h），配方经
   cache 变量把 qt5-qtbase 的 bin/moc 路径传入构建脚本；moc 运行期还需
   LD_LIBRARY_PATH 指向 qt5-qtbase/lib。
4. **上游特征门控默认差**（同一消费链坑位）：上游 CMakeLists 用选项门控
   编译宏（QZXING_USE_DECODER_* → ENABLE_DECODER_*），选项默认关而
   .pro/.pri 无条件开。按默认 CMake 打包的库运行时**静默缺特性**——
   qzxing 真机实证: 打包库 MultiFormatReader 零解码器、消费侧 decodeImage
   全灭，而按 .pri 宏编译的测试 harness 1110 图语料 851 成功。配方须按
   .pro 特征集显式全开。

## 推荐方案（实测配方形态）

```python
def generate(self):
    tc = CMakeToolchain(self)
    # ①消费走根 config，链接行不变；不设 Qt5_DIR、不碰原生伞形 config
    # ②moc 路径经 cache 变量传给补丁后的 CMakeLists（显式 moc）
    qt = self.dependencies["qt5-qtbase"]
    tc.cache_variables["QZXING_MOC_PATH"] = os.path.join(qt.package_folder, "bin", "moc")
    # ③按上游 .pro 特征集显式全开（上游 CMake 选项默认全关）
    tc.cache_variables["QZXING_USE_DECODER_QR_CODE"] = "ON"
    tc.cache_variables["QZXING_USE_DECODER_1D_BARCODES"] = "ON"
    tc.cache_variables["QZXING_USE_DECODER_DATA_MATRIX"] = "ON"
    tc.cache_variables["QZXING_USE_DECODER_AZTEC"] = "ON"
    tc.cache_variables["QZXING_USE_DECODER_PDF17"] = "ON"
    tc.generate()
    CMakeDeps(self).generate()
    # moc 运行期加载 qt5 库（构建期 LD_LIBRARY_PATH）
```

补丁侧: 库的 CMakeLists 改为 `find_package(qt5-qtbase)`，AUTOMOC 之外显式
`moc` 两个含 Q_OBJECT 的头。

## 验证（真机闭环）

- 三坑每步均为真机失败 → 修复闭环；修复后
  `QZXING_RESOURCES_DIR=<语料> conan create` 全绿（2026-09-30）:
  上游测试 1110 图语料 851 成功 / 237 失败 / 22 不一致（12/17 格式与上游
  参考日志逐字一致，失败为上游已知难例）+ 编码 46 方法全执行 + 打包
  libqzxing.so.3.3.0 + test_package 探针 8/8。
- 报告: archives/q/qzxing/3.3.0/reports/ohos-device-verification.md

## 关联条目

- E544（Qt5 qmake 转发桩打包，packaging 阶段，同属 Qt5 系不同阶段）
- qscintilla2 Qt6_DIR 范式（Qt6 伞形 config 可重定位，与 Qt5 相反，勿混用）
