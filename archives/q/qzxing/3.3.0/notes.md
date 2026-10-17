# qzxing 3.3.0 适配笔记

## 编译环境
- 构建系统: CMake（上游 src/CMakeLists.txt，打 1 个构建补丁 + 1 个测试夹具补丁）
- 编译器: clang/clang++（OHOS aarch64 profile）
- 依赖: qt5-qtbase/5.15.2（Qt5Core/Qt5Gui/Qt5Concurrent）
- 特征集: 全部解码器 + QR 编码器 ON；QML/multimedia OFF（与上游 QZXing.pro 默认一致，.pro 中这两块本来就是注释掉的）

## 上游信息
- 上游仓库: https://github.com/ftylitak/qzxing（git tag 3.3.0）
- 源码包: `https://deb.debian.org/debian/pool/main/q/qzxing/qzxing_3.3.0+dfsg.orig.tar.xz`
  （镜像 `https://mirrors.ustc.edu.cn/debian/pool/main/q/qzxing/qzxing_3.3.0+dfsg.orig.tar.xz`）
- sha256: `77a1be8df6b00c14583e04a6409ccdb4c26303f2d0e5b4e4ab2bec9a00cdad72`
  （2026-09-29 本地下载实测，与 Debian .dsc qzxing_3.3.0+dfsg-1.dsc 的 Checksums-Sha256 一致）
- 归档固定理由: github.com 直连 tarball 从调查网络仅 ~13KB/s 且超时（curl 28）；
  ghproxy.net 的 codeload 形式返回 14 字节错误页。按 implement-policy 固定到
  Debian orig。Files-Excluded（ci/、examples/QZXingLive、
  examples/QZXingDragNDropTest/qtc_packaging、examples/QMLBarcodeScanner/*.sis、
  src/zxing/win32）均不参与库构建：ci/ 与 examples 不在 src/CMakeLists.txt 内，
  zxing/win32 仅上游 WIN32 分支添加（且本配方 NO_ICONV 下亦不需要）。
- 许可证: Apache-2.0（LICENSE）

## 补丁说明（patches/0001-cmake-ohos-shared-build.patch）
1. `cmake_minimum_required(VERSION 3.3)` → `3.10`：CMake 4.x 拒绝 <3.5 的
   最低版本声明（policy E187，报错 "Compatibility with CMake < 3.5 has been
   removed"）。与 Debian 1004_cmake-4.patch 同款修复。
2. Qt5 消费改为 `find_package(qt5-qtbase)` 走 CMakeDeps 根 config，
   QML 三模块（Qt5Svg/Qt5Quick/Qt5QuickControls2）移入
   `if(QZXING_USE_QML)` 守卫、`Qt5Multimedia` 移入
   `if(QZXING_MULTIMEDIA)` 守卫（核心构建 OFF 不要求）。两层原因（真机
   实证）：
   a) qt5-qtbase 包内原生伞形 Qt5Config.cmake **不可重定位**——
      Qt5CoreConfig.cmake 引用构建机路径 `$PREFIX/../b//mkspecs/linux-clang`，
      二进制包在消费者机器上没有该构建目录，configure 直接报
      "imported target Qt5::Core references the file ... but this file does
      not exist"。
   b) conan 2 CMakeDeps **不生成**按模块的 Qt5Core-config.cmake 等单模块
      config（实测 conan 2.29：cmakedeps 模板对组件只输出根 config +
      共享 Targets + Target-release，模板代码里组件 cmake_file_name 零
      引用，无 Devel/组件文件机制）。正确姿势是 find_package(qt5-qtbase)
      根 config：它声明全部 Qt5::Core/Qt5::Gui/Qt5::Concurrent 组件
      target（组件 cmake_target_name 即 Qt5::*，链接行不变）。Qt6 的伞形
      config 可重定位（qscintilla2 的 Qt6_DIR 范式），Qt5 不可，勿混用。
3. `add_library(qzxing "" ${SOURCES})` → `SHARED` + `VERSION 3.3.0/SOVERSION 3`
   + `PRIVATE QZXING_LIBRARY`：QZXing_global.h 中 QZXING_LIBRARY 使
   QZXINGSHARED_EXPORT = Q_DECL_EXPORT；共享库交付（SONAME libqzxing.so.3，
   与 Debian libqzxing3 对齐）。
4. `PRIVATE NO_ICONV`：上游 CMake 仅在 WIN32/ANDROID/VS_WINRT 定义，
   Linux 走 iconv；.pri 路径对 !win32 一律 NO_ICONV。OHOS musl 的 iconv
   原型与 glibc 存在 ZXING_ICONV_CONST 分叉风险，取与上游 Android 一致的
   NO_ICONV 路径最稳。
5. 移除 `PUBLIC DISABLE_LIBRARY_FEATURES`：该宏使 QZXing 类不带导出宏
   （供 header-only/静态并入场景）；共享库构建保留它会剥掉 ABI 导出标记。
6. 显式 moc（QZXing.h/ImageHandler.h）：conan CMakeDeps 不设
   QT_VERSION_MAJOR，CMake AUTOMOC 检测不到 Qt5 自行禁用（dev warning），
   共享库会在无 metaobject 的情况下链接成功——共享库默认允许未定义符号，
   QZXing::staticMetaObject 留空在加载期才爆。moc 路径经 QZXING_MOC_PATH
   cache 变量由配方指向 qt5-qtbase 的 bin/moc（配方同时把 qt5-qtbase/lib
   放入 LD_LIBRARY_PATH 供 moc 运行期加载）；moc 带与编译一致的
   -DENABLE_ENCODER_GENERIC/-DENABLE_ENCODER_QR_CODE 保证 Q_ENUMS 字符串表
   一致。Linux 开发机无该变量时回退 find_program(moc)。

### 0002-fix-test-encode-fixture.patch（测试夹具修正）
- EncoderTests::testEncode 的期望字面量结尾与 QRCode::toString() 实际输出
  不符（`"\n>>\n"` vs `"\n\n>>"`，详见"上游测试审计"节），任何平台都无法
  通过。只改字面量结尾框架字符，矩阵 21 行不变；修正后 EncodeValidator
  单 try/catch 不再被该断言打断，46 个单元方法全部执行。

## 构建配置要点
- **解码器注册必须显式开**：MultiFormatReader.cpp 的每个解码器注册都被
  `#ifdef ENABLE_DECODER_*` 门控，而上游 src/CMakeLists.txt 只在
  `QZXING_USE_DECODER_*` CMake 选项为 ON 时才定义这些宏（选项默认全部
  未设置）。QZXing.pri 无条件定义全部宏，所以 .pro 构建带全部解码器；
  CMake 构建不开选项=打包出来的 MultiFormatReader **零注册解码器**，
  消费侧任何 decodeImage 都必败。真机实证：打包库解码全灭而同一批源码
  按 .pri 宏编译的测试 harness 1110 图语料 851 成功。配方在 generate()
  设 QZXING_USE_DECODER_{QR_CODE,1D_BARCODES,DATA_MATRIX,AZTEC,PDF17}
  =ON（与 QZXING_USE_ENCODER=ON 对称），对齐 .pro 特征集。
- **消费者坑（上游 API 缺陷）**：`QZXing(DecoderFormat)` 构造函数
  不初始化 tryHarderType（默认构造函数才 setTryHarderBehaviour），
  真机实测该构造函数实例的 getTryHarderBehaviour() 返回垃圾值 126——
  setTryHarder(true) 之后 ThoroughScanning 阶段仍不会执行。消费侧要么
  用默认构造 + setDecoder() + setTryHarder(true)（上游 DecodeValidator
  就是这个模式），要么显式 setTryHarderBehaviour()。test_package 探针
  按上游校验器模式书写。
- Qt5 消费：find_package(qt5-qtbase) 走 CMakeDeps 根 config（组件 target
  Qt5::Core/Qt5::Gui/Qt5::Concurrent 由根 config 声明，链接行不变）。
  不设 Qt5_DIR、不消费原生伞形 config（不可重定位），也不存在按模块
  Qt5Core-config.cmake（conan 2 CMakeDeps 不生成，见补丁说明 2）。
- 产物输出统一到 `<build>/lib`（CMAKE_LIBRARY_OUTPUT_DIRECTORY）。
- 共享库 ABI 三件套（libqzxing.so / .so.3 / .so.3.3.0）：HMDFS 拒 symlink
  （E046/E492 家族），构建期用 PATH ln shim（qt5-qtbase 配方同款，symlink
  失败自动 cp 回退）；打包期**三个名字一律 copy2 真实文件、不建 symlink**
  （CI #65168 教训：打包期 try symlink 首版对 libqzxing.so.3.3.0 自己建
  自引用链接，symlink 可用的 CI worker 上整条链悬空，CMakeDeps
  conan_package_library_targets() 的 find_library 见悬空链接 →
  "Library 'qzxing' not found in package"；真机 EPERM 走 copy2 才恰好
  通过，两环境包布局静默分化。全副本对任何文件系统确定）。
- OHOS 下共享库按仓库惯例做 ELF 签名：llvm-objcopy 去 .codesign 段 +
  binary-sign-tool sign -selfSign 1（qscintilla2 同款）。

## 上游测试审计
- 测试入口: `tests/src/QZXingTests/QZXingTests.pro`（qmake 工程；
  `QT += concurrent`，include(QZXing.pri) 把整个库源码编入测试二进制）。
  本配方用生成式 CMake harness 编译**同一批未修改的测试源**，define 与
  QZXing.pri 逐一对齐（QZXING_LIBRARY/DISABLE_LIBRARY_FEATURES/
  ZXING_ICONV_CONST/NO_ICONV/NOFMAXL/ENABLE_ENCODER_GENERIC/
  ENABLE_ENCODER_QR_CODE/ENABLE_DECODER_{1D_BARCODES,QR_CODE,DATA_MATRIX,
  AZTEC,PDF17}），规避 qmake mkspec 在 OHOS 设备上的不确定性。
- 编码侧: 7 个套件 46 个单元方法（MatrixUtilTests 11 / MaskUtilTests 5 /
  QRCodeTests 3 / EncoderTests 13 / ReedSolomonEncoderTests 1 /
  BitArrayTests 10 / BitVectorTests 3）。断言失败抛 zxing::Exception，
  被 EncodeValidator 捕获打印 "Exception:"——**输出无 Exception: 即 46/46 通过**。
- 上游测试缺陷（0002 补丁修正）：EncoderTests::testEncode 的期望字面量
  结尾写的是 `"...1 1 1\n>>\n"`，而 QRCode::toString() 在
  ByteMatrix::toString()（每行含末行都以 `\n` 结尾）之后追加 `"\n>>"`，
  实际输出结尾为 `"...1 1 1\n\n>>"`——断言在任何平台都无法通过（真机首跑
  字节级实证：26 行矩阵 dump 完全一致，仅结尾框架字符不同；上游 master
  同样字面量，且 appveyor.yml 的 test_script 为空=上游 CI 从不跑测试，
  缺陷从未被发现）。EncodeValidator 单 try/catch 包住全部 7 个套件，
  该断言一挂 EncoderTests 后续 ~10 个方法全被跳过。0002 只改字面量结尾
  框架字符（`">>\n"` → `"\n>>"`）使其与 toString 实际输出一致，矩阵
  21 行即该测试要钉住的内容未动；修正后 46/46 全部执行。
- 解码侧: 数据驱动，语料在 **git 子模块 qzxing-test-resources**（52 目录 /
  1192 PNG / 133MB），发行 tarball 不含。真机健康运行签名（2026-09-30
  实测）：**Total 1110、successful 851、failed 237、inconsistencies 22、
  17 条 per-format Decoder 行**。失败/不一致并非异常——上游自己提交的
  参考日志 tests/src/QZXingTests/qzxing_decode_3_0_alpha_0_3_test_results.log
  中 12/17 个格式的 (successful, failed, inconsistencies) 与真机逐字一致
  （AZTEC 13/21/2、CODABAR 11/0/0、CODE_39 23/0/2、CODE_93 3/0/0、
  CODE_128 47/1/1、DATA_MATRIX 26/11/0、EAN_8 8/0/0、EAN_13 120/37/2、
  ITF 21/6/0、PDF_417 39/21/1、UPC_E 47/8/2、UPC_EAN_EXTENSION 2/0/0、
  CODE_128_GS1 3/0/3），失败文件也按目录成簇（upca-6 整目录 19 张等），
  属上游已知难例。其余 5 个格式的差异全部是 3.0-alpha→3.3.0 的代码演进：
  RSS_EXPANDED 解码器重写（0/245→235/10）、QR_CODE 不一致 13→2、
  UPC_A 101/66/3→104/63/7、RSS_14 一张图由成功翻转为失败。配方验证器
  按 (1110, 851, 237, 22) 总签名 + 17 格式逐行表硬校验，语料更新时须同步
  刷新该表。
- 真机运行资源放置: 把子模块 checkout 放到
  `<source_folder>/tests/resources`（含 resources/ 子目录）即可；配方会把它
  链接/复制到 `<build_folder>/resources`（main.cpp 以 cwd 相对路径
  `../../resources/resources/` 解析）。更通用的做法: conan create 时设环境
  变量 `QZXING_RESOURCES_DIR=<checkout 路径>`，配方优先采用该目录（不设则回退
  到 source 树内路径，解码语料验证优雅跳过——上游打印 Total: [0]，46 个
  单元/编码方法照常执行并验证）。CI 与无语料环境均不设该变量。
- EncoderStressTest（--encoder-stress）为 opt-in 压力测试，默认不执行。
- 退出码不可靠（main() 无 return，恒 0）：验证必须解析 stdout，配方已在
  build() 内实现（_verify_upstream_output）。
- 测试二进制 runtime: QCoreApplication-only，无 QPA/插件依赖；QT_QPA_PLATFORM
  仅作环境保险。backward.hpp 默认 _Unwind_Backtrace（libgcc），musl 无
  execinfo 也安全。

## 已知限制
- QML（QZXingImageProvider）与 Multimedia（QZXingFilter）未启用：与上游
  .pro 默认一致；OHOS qt5-qtmultimedia 自身注释也承认设备端无
  pulse/alsa/gstreamer 运行时后端。
- Qt6 不在本版本范围：上游 README 声明 Qt6 需 core5compat 且编码能力降级；
  上游 3.3.0 CMakeLists 本身就是 Qt5-only。
