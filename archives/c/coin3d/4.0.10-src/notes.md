# coin3d 4.0.10-src 适配笔记

## 编译环境
- **构建系统**: CMake (NDK ohos.toolchain.cmake, CMAKE_SYSTEM_NAME=OHOS)
- **平台**: arm64-ohos (OpenHarmony PC), clang 15
- **状态**: built (conan-verify G0-G4/L2/L4/L5 全通过)
- **平台任务**: 6545 (coin3d/4.0.10-src, 主赛活动)

## 适配方案要点

1. **桌面 GL 的提供方式**: OHOS 仅提供 OpenGL ES。coin3d 链接注册仓
   `mesa/24.3.4.1`（libOSMesa 导出完整桌面 GL 入口 + 桌面 GL 头），
   CMake 侧用 `-DOPENGL_gl_LIBRARY/-DOPENGL_opengl_LIBRARY/-DOPENGL_INCLUDE_DIR`
   预置指向 mesa 包。coin 自身不创建窗口/GL 上下文，应用层负责
   （OSMesa 离屏上下文，或 EGL + gl4es）。
2. **X11/GLX/EGL 关停**: `COIN_BUILD_GLX=OFF`、`COIN_BUILD_EGL=OFF`，
   绕开 `find_package(X11 REQUIRED)`；X11 头仅 SoOffscreenGLXData.h
   引用，GLX 关闭后不参与编译。
3. **依赖链接策略**: Freetype/ZLib/BZip2/OpenAL 上游默认运行期 dlopen
   （*_RUNTIME_LINKING=ON），本配方改为 OFF 直接链接 Conan 依赖；
   GLU 与 FontConfig 保持运行期 dlopen（OHOS 无 libGLU/libfontconfig，
   运行期优雅降级，GLU 相关渲染能力受限——已知限制）。
   USE_SUPERGLU=OFF（仓内无 superglu）；USE_EXTERNAL_EXPAT=OFF（内置 expat）。
4. **testsuite 平台探测**: testsuite/TestSuiteUtils.cpp 以
   `_POSIX_C_SOURCE/_POSIX_SOURCE` 判定 POSIX/WIN32 分支，musl+clang
   在该检查点前不会预定义——配方注入 `-D_POSIX_C_SOURCE=200809L`
   选 POSIX 分支（零补丁）。
5. **消费者测试运行期库路径**: musl 加载器忽略 DT_RUNPATH 且 conan 2
   不向消费者二进制注入 rpath——test_package 的 test() 显式聚合全部
   （传递）依赖的 package lib 目录到 LD_LIBRARY_PATH 后直跑二进制。

## 上游测试（四维账本）

- N_static: 337（源码 142 个文件内嵌 COIN_TEST_SUITE 块，经 create_testsuite
  展开为 145 个 *Test.cpp，BOOST_AUTO_TEST_CASE 注册 337 例；其中含
  models 回归与 io/incorrect 文件用例的注册）
- N_executed: 325（CoinTests 直跑：[OK] 325 tests, 83466 checks，EXIT=0）
- N_pass: 325（0 失败）；337-325=12 为条件注册差额（VRML/JS 脚本引擎
  未启用相关注册，运行日志无 skip 行，注册表在无 JS 引擎时收缩），
  与配方 COIN_HAVE_JAVASCRIPT=OFF 的上游条件编译语义一致
- 文件回归: models/*.iv 107 个（testCorrectFile）+ io/incorrect 15 个
  （testIncorrectFile），均包含在上述 325 例中
- N_consumer: 1（test_coin3d：SoDB::init + SoCube 场景图包围盒断言 3 +
  .iv 序列化往返（SoWriteAction→SoInput→SoDB::readAll）+ 字段恢复断言 3，
  共 7+ 断言，退出码判定）

## 本地调试过程坑（不进 PR 的过程记录）

- conan-verify 的 E017 ghfast.top 镜像注入会改写 conandata URL：
  本地 dlcache 预置（AGENTS §12.3）时 sidecar 必须同时登记官方 URL
  与注入后 URL，否则缓存被判 dirty 强制回源（设备到 ghfast.top 不通）。
- 消费者测试"符号找不到"假象：设备内存高压窗口（MemFree<600MB）下
  共享库 mmap 失败被 musl 报成 "Error loading shared library /
  symbol not found"；绿窗时同一二进制+同一库实跑 PASS。择窗重跑即可。

## 已知限制

- 无 GLU（OHOS 无 libGLU.so）：GLU 依赖的 NURBS/mipmaps 等渲染路径
  运行期降级。
- FontConfig 运行期不可用：字体检索回退 freetype 直连路径。
- simage/SpiderMonkey 未启用（上游可选组件，仓内无对应包/无 JS 引擎）。
- OpenAL 已链接，但 OHOS 音频后端可用性取决于运行环境。
---

**编译结束**: 2026-09-15 07:53
**最终状态**: built
