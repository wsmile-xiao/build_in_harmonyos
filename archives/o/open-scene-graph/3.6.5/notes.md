# open-scene-graph 3.6.5 适配笔记

## 编译环境
- 构建系统: cmake (Ninja)
- 编译日期: 2026-09-10
- 编译器: clang/clang++ (OHOS SDK)
- 状态: built
- 任务: 平台任务 #5578（同版本重做，测试闭环为主）

## 同版本重做说明

main 上 `archives/o/openscenegraph/3.6.5/` 是搭 !8468 进 main 的元数据残留
（只有 manifest/notes/patches/reports，无 conanfile.py）。本任务在
`archives/o/open-scene-graph/3.6.5/` 新目录从零重做完整配方
（目录名带连字符 —— L0n 从目录名推期望分支 feat/open-scene-graph-3.6.5），
残留旧目录不动。制品仓未发布该包，同版本重做合法。

## 上游测试 N 实测（2026-09-10 源码审计）

- 下载 OpenSceneGraph-3.6.5 tag 源码全文扫描：**0 个 add_test / enable_testing**
  （CTestConfig.cmake 仅配置 CDash dashboard 提交地址，从未注册测试目标）
- 上游"测试"形态 = examples/ 交互式 GPU 演示（BUILD_OSG_EXAMPLES 默认 OFF），
  需要显示服务器 + GPU，无头 CI 不可运行
- 与 main 残留 test-report.md 结论一致（"No tests found"）
- **N=0，无可跑项，无逐项豁免**——申报口径按上游默认形态的注册口径为 0

替代验证链（无 GPU 环境）：
1. 构建期 smoke：conanfile.build() 运行已构建 osgversion 二进制（打印版本串）
2. test_package 消费者测试：链接 libosg/libosgDB/libOpenThreads，调用
   osgGetVersion/osgDB::Registry::instance()/OpenThreads::GetNumberOfProcessors，
   并运行打包的 osgversion

## 编译配置（GLES3 profile，无窗口系统）

```bash
cmake -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DOPENGL_PROFILE=GLES3 \
  -DOSG_GLES3_AVAILABLE=ON \
  -DOSG_GL1_AVAILABLE=OFF -DOSG_GL2_AVAILABLE=OFF -DOSG_GL3_AVAILABLE=OFF \
  -DOSG_GLES1_AVAILABLE=OFF -DOSG_GLES2_AVAILABLE=OFF \
  -DOSG_GL_FIXED_FUNCTION_AVAILABLE=OFF -DOSG_GL_DISPLAYLISTS_AVAILABLE=OFF \
  -DOSG_GL_MATRICES_AVAILABLE=OFF -DOSG_GL_VERTEX_FUNCS_AVAILABLE=OFF \
  -DOSG_GL_VERTEX_ARRAY_FUNCS_AVAILABLE=OFF \
  -DOSG_WINDOWING_SYSTEM=None \
  -DBUILD_OSG_EXAMPLES=OFF -DBUILD_OSG_APPLICATIONS=ON -DBUILD_OSG_PLUGINS=ON \
  -DOSG_TEXT_USE_FONTCONFIG=OFF \
  -DBUILD_SHARED_LIBS=ON \
  -DOPENGL_INCLUDE_DIR=<sysroot>/usr/include \
  -DOPENGL_gl_LIBRARY=<sysroot>/usr/lib/aarch64-linux-ohos/libGLESv3.so \
  -DEGL_INCLUDE_DIR=<sysroot>/usr/include \
  -DEGL_LIBRARY=<sysroot>/usr/lib/aarch64-linux-ohos/libEGL.so
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 HarmonyOS 为 UNIX | 上游 2.6 时代 CMakeLists 只认 IF(UNIX) | E092：CMAKE_SYSTEM_NAME=Linux + aarch64；补丁 0001 加 HarmonyOS 回退（原生构建用） |
| 2 | sys/unistd.h 不存在 | OHOS musl sysroot 无此头 | 补丁 0003 改用 unistd.h |
| 3 | pthread_cancel 等函数不存在 | musl 不实现线程取消 | 补丁 0002 CHECK_FUNCTION_EXISTS 探测后再定义 |
| 4 | CMake 版本兼容 | cmake_minimum_required(2.6) | CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 5 | OpenGL/EGL 找不到 | FindOpenGL 不支持 GLES-only sysroot | 手动注入 OPENGL_INCLUDE_DIR/OPENGL_gl_LIBRARY/EGL_LIBRARY 指向 OHOS sysroot |
| 6 | 三方插件依赖拉不齐 | freetype/png/jpeg/tiff/curl 等在制品仓版本分散 | 全部置 NOTFOUND，上游跳过对应插件，保持零 conan 依赖 |
| 7 | GNU make 在 OHOS worker 失败 | /bin/sh execute-only，make 无法 stat | Ninja generator + CMAKE_C(XX)_COMPILER_WORKS=TRUE 跳过 try-compile |
| 8 | OpenThreads CheckAtomicOps try_run 失败 | 交叉编译模式 try_run 不可执行 | 预置 _OPENTHREADS_ATOMIC_USE_GCC_BUILTINS_EXITCODE=0（上游 examples/osgemscripten 同款方案） |
| 9 | tristripper/obj 插件编译失败 | std::mem_fun_ref/std::ptr_fun/not1 C++17 移除 | 补丁 0004（显式循环）/ 0005（lambda） |
| 10 | cfg 插件编译失败 | lex/yacc 生成代码用 register 关键字（C++17 移除） | CMAKE_CXX_FLAGS=-Wno-register 降级 |
| 11 | 包产物库无法被 musl loader 加载 | CMake install 期 RPATH 重写（file(RPATH_CHANGE)）在 HMDFS 上损坏 ELF（实测：构建树副本可加载、安装副本不可加载，哈希不同） | CMAKE_BUILD_WITH_INSTALL_RPATH=ON + CMAKE_INSTALL_RPATH="" 使 install 变纯复制 |
| 12 | 包目录产物 execve/加载被拒 | HMDFS 对 conan 缓存包目录限制执行 | test_package 将包内库与 osgversion 字节级镜像到 build 目录再运行（SDL2_image mirror 同款思路） |
| 13 | 运行时符号解析失败 | musl loader 需 /system/lib64 优先（系统 libEGL/libhilog 依赖系统 libc++.so） | LD_LIBRARY_PATH 顺序：/system/lib64 → 镜像库目录 → NDK libc++_shared 目录 |

## 依赖版本

- EGL/GLESv3: 系统库（/system/lib64/libEGL.so, libGLESv3.so，构建期用 sysroot 桩库）
- 无 conan 依赖（W0 核验）

## 验证结果

- conan create 全量构建（核心库 + 无依赖插件 + 应用程序）
- build 阶段 smoke：osgversion 运行打印 OpenSceneGraph 3.6.5
- test_package：test_osg_consumer 链接并调用核心 API，全部断言通过

## 注意事项

- GLES3 模式（无桌面 OpenGL），无 X11 窗口系统；3D 渲染需消费者自行提供
  EGL graphics context（系统 libEGL/libGLESv3 运行时加载）
- 上游无 ctest 注册测试：N=0，CI L1 以 build 内 smoke + test_package 为准

## CI Worker 环境坑（2026-09-11 修复轮）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 14 | CI Worker configure 失败：CMake Error at ~/usr/local/lib/cmake/freetype/freetype-config.cmake:91（imported target 引用不存在的 ~/usr/local/lib/libfreetype.a 绝对路径） | 已发布 freetype 包的 cmake 配置带打包者本机绝对路径（坏包残留，libX11-xcb.la 悬空路径同款问题）；旧方案仅将 FREETYPE_LIBRARY 等结果变量置 NOTFOUND，但 find_package 在 config-mode 仍会加载坏 freetype-config.cmake | generate() 改用 CMAKE_DISABLE_FIND_PACKAGE_<Pkg>=True 短路全部三方插件依赖的 find_package（Freetype/JPEG/PNG/TIFF 等 31 个 + X11），CMake 对该变量的官方语义是「视为 not found，不做任何搜索、不加载任何 config」——上游 CMakeLists 735 行注释自荐的同款手法 |
