# juce 8.0.5 — HarmonyOS PC 适配说明

- 官方归档：https://github.com/juce-framework/JUCE/archive/refs/tags/8.0.5.tar.gz
  （SHA256 f0b7a2a255f70d24213dde219ac410333f72a1a6fe0db33342c5e62813b808eb，
  单一根目录 JUCE-8.0.5/）。
- license：modules 双许可 AGPLv3 / JUCE 8 商业 EULA（tag 树 LICENSE.md），
  配方登记 FOSS 侧 AGPL-3.0-or-later；examples 为 ISC；内嵌第三方
  （VST3 SDK = GPLv3/Steinberg 双许，FLAC/OGG = BSD，harfbuzz = Old MIT，
  SheenBidi = Apache-2.0 等）随源码分发。
- 分发形态：23 个模块为 INTERFACE 目标（源码由消费方目标编译），官方
  install 产出 JUCEConfig.cmake（lib/cmake/JUCE-8.0.5）+ 构建期工具
  juceaide / juce_lv2_helper / juce_vst3_helper（bin/JUCE-8.0.5）。消费方
  find_package(JUCE) 后以 juce_add_console_app / target_link_libraries
  (juce::juce_core ...) 使用；cpp_info 设 cmake_find_mode=none 防止
  CMakeDeps 生成占位 config 抢占原始 JUCEConfig。
- juceaide：configure 期由上游自带引导流程原生构建（OHOS 真机 build==host），
  install 以 IMPORTED juce::juceaide 落入包内 config，消费方无需嵌套构建。
- 平台开关（包级默认，源内联补丁）：JUCE_WEB_BROWSER=0（webkit2gtk 全仓无
  配方）、JUCE_USE_CURL=0（上游原生工具同款；juce_Network_linux.cpp 有完整
  非 curl 路径）、JUCE_ALSA=1（alsa-lib 已发布）、JUCE_JACK=0（上游默认）、
  JUCE_USE_XRENDER=0（上游默认，连带免 Xcomposite）、X11 扩展 XRANDR/
  XINERAMA/XSHM/XCURSOR=0（OHOS 无 X server，核心几何回退路径足够；仅保
  留核心 libx11 头经 linuxPackages NOLINK 提供，运行期 JUCE 全 dlopen，不
  产生 DT_NEEDED；并规避 libxrender 源码重建被 OHOS uname 打挂 config.guess
  与 xorgproto 2024.1/2025.1 图内冲突）。
- CMake 平台：配方与 test_package 强制 CMAKE_SYSTEM_NAME=Linux（E092 先例）；
  同时 JUCEModuleSupport.cmake 补丁让 HarmonyOS 并入 Linux 族（架构探测、
  _linux 源选择、LINUX=1、linuxPackages/linuxLibs 元数据链接），未强制该
  变量的下游 find_package(JUCE) 亦可工作。
- X11 协议头：linuxPackages 声明 `NOLINK x11 xproto`。libx11/6.4.0 包内
  只含 libX11 自身构建的头；X11/Xatom.h、X11/Xmd.h、X11/keysym.h 等
  协议头由 xorgproto/2025.1 提供（与 libx11 依赖同版本，clxclient/3.9.0
  先例）。xorgproto 自带真实 .pc（share/pkgconfig，${pcfiledir} 相对
  前缀）且未声明 pkg_config_name，PkgConfigDeps 不代生成——消费方
  generate() 需将其 share/pkgconfig 并入 PKG_CONFIG_PATH（test_package
  内置示范）。JUCE 上游 X11 扩展头（Xrandr/Xinerama/XShm/Xrender/
  Xcomposite/Xcursor）均有 JUCE_USE_* 守卫，包级默认全 0，不引这些库。
- musl/OHOS libc 补丁（3 处）：juce_core.h JUCE_USE_CURL 默认 0；
  juce_SystemStats_linux.cpp glibc _NL_ADDRESS_* 宏加 __OHOS__ 兜底；
  juce_Threads_linux.cpp Thread::killThread 的 pthread_cancel no-op
  （adlplug 1.0.2 同款先例）。
- 字体链运行期（E505）：freetype/2.14.3 + fontconfig/2.18.3 + libxml2/2.15.3
  取已发布共享库（fontconfig 2.18.3 上游 meson 要求 >=1.11，本机系统 meson
  1.5.1 无法静态重建）；OHOS musl 加载器无法经版本化符号链接别名解析 .so
  （E505），故：配方 generate() 把三者 .so 真实文件实体化进包内
  lib-juceaide-runtime/ 并改写生成的 freetype2.pc/fontconfig.pc 的 Libs 行
  注入 DT_RPATH（--disable-new-dtags，绝对路径 + $ORIGIN 相对路径），使
  juceaide（真链接字体链）在构建期与消费方 configure 期可直接运行；实体化
  后逐个 binary-sign-tool selfSign 签名（OHOS 安全策略：用户存储 .so 未签名
  dlopen 即 EACCES；经验仓 mlton-20241230/alsa-lib/bam 先例）；消费方二进制
  按同一范式实体化+签名+嵌 rpath（test_package 内置示范，运行时 unset
  LD_LIBRARY_PATH 防其压过 DT_RPATH）。
- juce_opengl 的 linuxPackages=gl 由 mesa/24.3.4.1.1 提供（mesa.pc 需消费方
  generate() 转发 gl.pc，PkgConfigDeps pkg_config_name 映射，E348 手法）；
  本配方 test_package 不编译 juce_opengl。
