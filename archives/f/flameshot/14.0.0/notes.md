# Flameshot 14.0.0 OpenHarmony PC 适配笔记

## 项目简介

Flameshot 是一款功能强大且简单易用的截图软件（Qt Widgets GUI 应用），支持
区域/全屏/窗口截图、标注、上传等功能。本适配将 Flameshot 14.0.0 以 Qt5
工具链（制品仓 qt5-qtbase/5.15.2.2 + qt5-qtsvg/5.15.2.1）构建为 OHOS
aarch64 应用。

## 上游信息

- 官网：https://flameshot.org
- 源码仓库：https://github.com/flameshot-org/flameshot
- 发布 tag：`v14.0.0`
- 源码包 SHA-256：`810c399f3b9fbfd72e24e61417ede24243925f9c0d03040a8aba0d4866676d93`
- 许可证：GPL-3.0

## 构建配置

- CMake 构建；Qt5（QT_DEFAULT_MAJOR_VERSION=5, QT_VERSION_MAJOR=5）
- 内嵌 Qt-Color-Widgets（gitlab 固定 commit 5d52e907）与 KDSingleApplication
  （v1.2.0）作为 `external/` 子项目，随源码阶段下载，构建不依赖网络
- 关闭更新检查（DISABLE_UPDATE_CHECKER=ON）与 Imgur 上传（ENABLE_IMGUR=OFF）
- 产物：`bin/flameshot`（OHOS aarch64 ELF，动态链接 Qt5）

## OHOS 适配要点

1. **Qt5 而非 Qt6**：上游 14.0.0 面向 Qt6 API，制品仓仅 Qt5，共 14 个
   可移植性补丁桥接 Qt6→Qt5 差异（enterEvent、retrieveData、
   QFontDatabase::families、QLibraryInfo::path、QSharedMemory、
   DBus 源文件在 OHOS 编译等）。
2. **版本覆盖依赖**：qt5-qtsvg 硬编码依赖 qt5-qtbase/5.15.2，而 Flameshot
   需要含 DBus 的 qt5-qtbase/5.15.2.2，配方用 override 统一版本；此时
   CMakeDeps 不再导出 Qt5 的 include/链接元数据，配方显式注入：
   - `FLAMESHOT_QT5_INCLUDE_DIR`（include 根 + 全部 Qt* 子目录）
   - `-lQt5Core -lQt5Gui -lQt5Widgets -lQt5Network -lQt5DBus` 链接标志
   - `CMAKE_AUTOMOC/AUTORCC/AUTOUIC_EXECUTABLE` 指向 qt5-qtbase 的
     moc/rcc/uic
3. **SDK toolchain 查找限制**：ohos.toolchain.cmake 设置
   `CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY`，需把 generators 目录加入
   `CMAKE_FIND_ROOT_PATH` 才能命中 CMakeDeps 生成的 Qt5 配置。
4. **llvm-ranlib 缺失**：SDK 指向不存在的 llvm-ranlib，改用宿主的
   `/data/service/hnp/bin/llvm-ranlib`。
5. **Qt5 特性裁剪**：qt5-qtbase 无 LinguistTools（翻译 .ts 生成跳过）、
   无 qstringconverter（QStringDecoder→fromUtf8/toUtf8）、
   无 sharedmemory 特性（QSharedMemory 单实例锁→KDSingleApplication 兜底）。

## 依赖

- qt5-qtbase/5.15.2.2（含 Qt5DBus）
- qt5-qtsvg/5.15.2.1（Qt5::Svg）
- 内嵌 Qt-Color-Widgets、KDSingleApplication（随配方下载）

## 已知限制

- OHOS 严格执行上下文（CI worker 沙箱、部分 shell）拒绝执行未签名 ELF
  （`Operation not permitted`）：test_package 保留沙箱降级逻辑（WARN）
  以兼容沙箱化 CI；非沙箱环境需先用 `binary-sign-tool sign -selfSign 1`
  签名后执行。
- 翻译（.qm）未生成（无 LinguistTools），界面为英文。
- Imgur 上传与自动更新检查已禁用。

## 验证

- conan create 完整构建通过（强制重建：`conan create ... --build=missing`
  多次迭代后成功产出包）。
- 新增测试实测通过：鸿蒙 PC 设备非沙箱上下文执行包内 `bin/flameshot`
  （binary-sign-tool 签名后，`QT_QPA_PLATFORM=offscreen`），
  `flameshot --version` 输出 `Flameshot v14.0.0 ()` / `Compiled with Qt 5.15.2`，
  test_flameshot.sh 断言 PASS（exit 0）。
