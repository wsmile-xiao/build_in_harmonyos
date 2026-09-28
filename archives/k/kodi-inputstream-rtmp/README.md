# kodi-inputstream-rtmp

Kodi 官方的 RTMP 输入流二进制插件（`inputstream.rtmp`）：让 Kodi 及其插件通过
RTMP/RTMPT/RTMPE/RTMPTE/RTMPS 协议拉取实时/点播流媒体，支持 SWF 验证
（swfUrl/swfVfy）、页面来源伪装（pageUrl）与播放路径（playpath）等 librtmp 选项。

## 功能概述

- 以 Kodi inputstream 实例插件形式提供 RTMP 网络流（协议点：`rtmp|rtmpt|rtmpe|rtmpte|rtmps`）
- 基于 librtmp：会话建立（RTMP_Init/RTMP_Connect）、按帧读取（RTMP_Read）、暂停检测、Seek（RTMP_SendSeek）
- 读写超时看门狗（src/timer/Timer.cpp 独立线程定时器）

## OHOS 适配

- 上游构建依赖 Kodi 构建系统（`find_package(Kodi)` 提供 `build_addon()` 宏与
  `KODI_INCLUDE_DIR`），registry 中无 kodi 包：配方自带 `recipe-cmake/`
  CMake 入口（`build_script_folder` 消费），对上游源码零修改构建同一份
  `src/RTMPStream.cpp + src/timer/Timer.cpp`（kodi-platform 先例）。
- Kodi C++ 插件头文件（`<kodi/General.h>`、`<kodi/addon-instance/Inputstream.h>`）
  取自 xbmc 21.3-Omega 归档的 `xbmc/addons/kodi-dev-kit/include/kodi`，其 kodi/
  子树原样内嵌于版本目录 `kodi-dev-kit/kodi`；inputstream instance API 3.3.0
  与插件源码的全部 override 签名核对兼容。
- 上游 `FindRTMP.cmake` 走 pkg-config 找系统 librtmp；改为链接 Conan CMakeDeps
  的 `librtmp::librtmp` target（静态库编入插件 .so），并补 include 父目录以支持
  上游 `<librtmp/rtmp.h>` 风格包含。
- 产物为单一共享模块（上游名 `inputstream.rtmp.so`，包内标准前缀
  `libinputstream.rtmp.so`）；`addon.xml.in` 等安装期元数据由 Kodi 宿主打包流程
  展开（`@ADDON_DEPENDS@`/`@PLATFORM@` 占位符），不属于本包职责。
- 上游无测试套件（无 enable_testing/add_test、无 tests 目录），test_package 为
  消费者级链接+运行验证（共 21 项断言）：API 版本纯函数断言，以及经
  dlopen/dlsym ADDONCREATOR 工厂导出走一次真实宿主桩声明/打开流程
  （实例化 CInputStreamRTMP、GetCapabilities 精确断言、非法/不可达 RTMP URL
  受控失败传播、销毁清理）。

## 依赖关系

编译与运行依赖：

- `librtmp/2.4_git20190330`（conan，静态 PIC 编入模块）
- `openssl/3.5.6`（conan，静态 PIC 编入模块；RTMPE/RTMPS 握手、SWF SHA256）
- zlib：链接 OHOS 系统 `libz.so`（conan zlib/1.3.1 为静态非 PIC 归档，
  不能链入共享模块；产物 DT_NEEDED=libz.so，运行时由加载器按
  /etc/ld-musl-aarch64.path 默认搜索路径解析到系统组件
  /system/lib64/chipset-sdk-sp/libz.so（→ libshared_libz.z.so），
  无需 LD_LIBRARY_PATH）

## 参考资料

- 上游仓库：<https://github.com/xbmc/inputstream.rtmp>
- 归档 tag：`21.1.2-Omega`
- Kodi add-on 开发文档：<https://docs.kodi.kz>
