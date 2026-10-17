# kodi-pvr-iptvsimple

Kodi 官方的 IPTV Simple PVR 客户端二进制插件（`pvr.iptvsimple`）：为 Kodi 提供
IPTV 直播/回看后端——M3U 播放列表、XMLTV EPG、频道/频道组/提供商，以及基于
inputstream 插件的流播放与电台支持。

## 功能概述

- 以 Kodi PVR client 实例插件形式提供 IPTV 后端（`ADDON_INSTANCE_PVR`）
- M3U/M3U8 播放列表解析与定时刷新（`PlaylistLoader`，支持 gzip/xz 压缩列表）
- XMLTV EPG 拉取与查询（`Epg`），频道/组/提供商（`Channels`/`ChannelGroups`/`Providers`）
- 回看（catchup）与流属性注入（`CatchupController`/`StreamManager`）
- 多实例设置与旧版设置迁移（`SettingsMigration`）

## OHOS 适配

- 上游构建依赖 Kodi 构建系统（`find_package(Kodi)` 提供 `build_addon()`/
  `addon_version()` 与 `KODI_INCLUDE_DIR`），registry 中无 kodi 包：配方自带
  `recipe-cmake/` CMake 入口（`build_script_folder` 消费），对上游源码零修改
  构建同一份 `src/` 树（kodi-inputstream-rtmp / kodi-addon-screensaver 先例）。
- Kodi C++ 插件头文件（`<kodi/AddonBase.h>`、`<kodi/addon-instance/PVR.h>`、
  `<kodi/addon-instance/pvr/*>`）取自 xbmc 21.3-Omega 归档的
  `xbmc/addons/kodi-dev-kit/include/kodi`，其 kodi/ 子树原样内嵌于版本目录
  `kodi-dev-kit/kodi`；PVR instance API 8.3.0（min 8.2.0）与 21.11.0 插件的
  Omega（21.x）代码一致，全部 `CInstancePVRClient` override 均可解析。
- 上游 `Findpugixml.cmake`/`Findlzma.cmake`（pkg-config 风格）改为 Conan CMakeDeps
  的 `pugixml::pugixml` / `lzma::lzma`；zlib 链系统 `z`。
- 产物为单一共享模块 `pvr.iptvsimple.so`（`MODULE` + `PREFIX ""`，与 addon.xml 的
  `library_linux` 期望名一致；显式相对 SONAME）；`addon.xml.in` 的
  `@ADDON_DEPENDS@`/`@PLATFORM@`/`@LIBRARY_FILENAME@` 占位符由 Kodi 宿主打包流程
  展开，不属于本包职责。
- **OHOS 关键点**：CMake `--install` 的 RPATH 改写会就地修改产物 ELF，触发 OHOS
  加载器的整文件完整性校验（`dlopen` 报 EACCES/Permission denied）；配方置
  `CMAKE_SKIP_RPATH=ON`，使安装产物与链接器输出逐字节一致后恢复正常（详见
  `21.11.0/notes.md`）。
- 上游无测试套件（无 enable_testing/add_test、无 tests 目录），test_package 为
  消费者级真实链接+运行验证（共 25 项断言）：Kodi 二进制插件 C ABI 契约断言、
  产物导出的 `FileUtils::GzipInflate`/`XzDecompress` 真机解压路径验证，外加
  鸿蒙专项测试（RTLD_NOW 即时绑定、zlib 解析到 OHOS 系统 libz 的 dladdr 取证）。

## 依赖关系

编译与运行依赖：

- `pugixml/1.15-r0`（conan，静态编入模块；上游 pin 1.14，同 1.x 系列兼容）
- `lzma/5.6.2`（XZ Utils，conan，静态 PIC 编入模块；上游 pin xz-utils 5.4.3）
- zlib：链接 OHOS 系统 `libz.so`（conan zlib/1.3.1 为静态非 PIC 归档，不能链入
  共享模块；产物 DT_NEEDED=libz.so，运行时由 OHOS 加载器解析到系统组件
  /system/lib64/platformsdk/libz.so，test_package 的 dladdr 实测取证）
- 网络/文件访问走 Kodi 宿主接口（`kodi::vfs` / `kodi::network`），无外部 curl 依赖

## 参考资料

- 上游仓库：<https://github.com/kodi-pvr/pvr.iptvsimple>
- 归档 tag：`21.11.0-Omega`
- Kodi add-on 开发文档：<https://docs.kodi.tv>
