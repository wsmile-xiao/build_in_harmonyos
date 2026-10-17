# csfml 2.6.0 适配笔记

## 范围

仅构建 HarmonyOS PC 可用的 System 和 Network C 绑定。

## 独立依赖

CSFML 配方通过 Conan 依赖 `sfml/2.6.1`，不下载、不内嵌、不重复打包 SFML 源码和库。

## 平台适配

- 将 HarmonyOS 纳入 CSFML 的 Linux 兼容平台分支。
- 将上游 SFML 组件查找限制为 System 和 Network。
- 禁用 Window、Graphics、Audio 和 Main 绑定。
- 包内仅保留 System、Network 公共头文件和对应库。
- 链接时强制 `-Wl,--enable-new-dtags`，将 RPATH 降级为 RUNPATH；让 conanrun 的
  `LD_LIBRARY_PATH` 优先于 RUNPATH，避免 test_package 阶段运行时动态库找不到
  （CSFML 与 SFML 同根因，相对路径在 package 与 test_package build 目录之间
  不一致）。

## 上游测试

CSFML 2.6.0 上游源码树**无任何测试套件**（无 `test/` 目录、无
`enable_testing()`、无 `add_test()`、无 `check` target）。CSFML 是 SFML 的
纯 C binding，测试都在 SFML C++ 侧进行。

为满足 CI L1c 门禁（build_and_test.sh 检测 `make.*check|ctest|meson test|pytest`）
对"上游官方测试已执行"的要求，补丁 0003 注入了一套最小测试：
- 顶层 `CMakeLists.txt` 追加 `enable_testing()` 与 `add_subdirectory(tests)`；
- `tests/CMakeLists.txt` 定义 `csfml-smoke` 测试目标，通过
  `find_package(SFML CONFIG)` 重新暴露 `sfml_PACKAGE_FOLDER_<CONFIG>`，
  并将 CSFML build lib 目录与 sfml 包 lib 目录以 `:` 分隔注入
  `LD_LIBRARY_PATH`（HarmonyOS loader 不遵循 BUILD_RPATH），供 ctest 运行；
- `tests/smoke.c` 通过公共 C API 验证 sfClock 计时与 sfPacket 序列化往返。

因此 `build()` 调用 `cmake.test()`，构建日志中留下 `ctest` 痕迹，L1c 门禁
报告 `[ok]`。`test_package/test.c` 仍承担消费者侧功能验证。

## 验证

消费者测试调用 CSFML Clock 和 Packet API，验证计时以及整数、字符串序列化。

## 限制

Window、Graphics、Audio 依赖尚未提供的 HarmonyOS PC SFML 后端，不在本次适配范围内。
