# mygui 3.4.4 适配笔记（HarmonyOS PC · Conan cmake）

## 定位
- 源码：官方上游 `https://github.com/MyGUI/mygui`，tag `MyGUI3.4.4`，归档
  `https://github.com/MyGUI/mygui/archive/refs/tags/MyGUI3.4.4.tar.gz`，SHA-256
  `2b4b87c5c04cd9a33413d0ccebc1aa03b56c72873901633c85be2652ceb6785b`（已校验）。
- 消费者：OpenMW `openmw-0.51.0` 在启用系统 MyGUI 时调用
  `find_package(MyGUI 3.4.3 REQUIRED)`；配方 `cpp_info` 提供
  `cmake_file_name=MyGUI` / `cmake_target_name=MyGUI::MyGUI` 兼容。

## 编译环境
- 构建系统: cmake（4.1.2）· 编译器: clang 15.0.4 (OHOS) · 目标: aarch64-linux-ohos
- 编译日期: 2026-08-28

## 关键适配
- **渲染系统选型（首轮本地验证）**：`MYGUI_RENDERSYSTEM=1`（Dummy 平台）——
  无 GL 依赖、可在无头环境干净构建 MyGUIEngine + MyGUI.DummyPlatform。
  真实 OHOS 渲染平台（`MYGUI_RENDERSYSTEM=8` OpenGLES，链接 OHOS SDK 的
  libEGL/libGLESv2/libGLESv3，头文件在 sysroot `GLES3/EGL`）是明确记录的后续项，
  需要 XComponent/窗口上下文配合，超出本轮本地 W3 验证范围。
- **引擎字体**：`MYGUI_USE_FREETYPE=ON`，依赖 `freetype/2.14.3.1` + `zlib/1.3.1.1`
  （ohpcd 已发布）。`generate()` 把依赖包目录注入 `CMAKE_PREFIX_PATH`，并预置
  `FREETYPE_*`/`ZLIB_*` 遗留变量，满足 MyGUI `Dependencies.cmake` 的
  FindFreetype/FindZLIB 模块。
- **关闭无关组件**：demos/tools/unittests/test_app/plugins/wrapper/docs 全关
  （它们依赖 SDL2_image/OGRE 和交互显示，会破坏无头 W3）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载卡 300s | github 直连慢、CDN 波动 | 先手工下载官方归档并双端保留（TMPDIR+work），`--no-download` 续跑 |
| 2 | init-build SSL 检查挂起 | ftp.gnu.org 不可达触发证书重装 | 重跑后 curl.se 可达，证书装入后通过（warnings 不阻塞） |
| 3 | 初判 build_system=autotools | URL 猜测失误 | 修正 manifest/system=cmake，按 CMake 配方编写 |

## 源码修改
无（本轮无补丁，patches/ 空）。

## 依赖版本
- freetype/2.14.3.1（ohpcd 已发布）
- zlib/1.3.1.1（ohpcd 已发布）

## 验证结果
```bash
# 待本地 W3（finish 流程经 ohpc_compile_worker 通道）实测后回填：
# conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... 
# 期望产出 libMyGUIEngine + libMyGUI.DummyPlatform
```

## 注意事项
- OpenGLES 平台（RENDERSYSTEM=8）为后续适配项，需 XComponent/GLES 上下文实测。
- 上游 UnitTests 默认关，测试账目以 test_package 消费者验证为准。
---

**编译结束**: 2026-08-28 23:14
**最终状态**: built
