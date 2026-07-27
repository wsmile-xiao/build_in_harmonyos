# xerces-c 3.2.5 适配笔记

## 上游与版本
- 上游：Apache Xerces-C++ 3.2.5（2023-12-20 发布）
- 官方源：`https://archive.apache.org/dist/xerces/c/3/sources/xerces-c-3.2.5.tar.gz`
- sha256：`545cfcce6c4e755207bd1f27e319241e50e37c0c27250f11cda116018f1ef0f5`（与官方 `.sha256` 校验文件一致）
- License：Apache-2.0
- 构建系统：CMake（`cmake_minimum_required(VERSION 3.12.0)`，固定 C++14）

## 平台检测分析（关键）
xerces-c 的 CMake 平台判定全部走通用 `UNIX`/`WIN32`/`APPLE` 标志（见 `cmake/Xerces*.cmake` 各选择模块与 `grep "STREQUAL \"Linux\""` 无命中），**没有** `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 这类 OS 专属分派。因此：
- OHOS conan profile 把 `os=OHOS` 自动映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，xerces-c 在 HarmonyOS 名下走与 Linux 一致的 UNIX 通用分支，行为不变。
- 对比 nsync 等库（有 `STREQUAL "Linux"` → 误入 Linux futex 分支 → musl 报错），xerces-c **无此坑**，无需 `tc.variables["CMAKE_SYSTEM_NAME"]="OHOS"` 强制改写。

## 三个后端为何显式钉死
xerces-c 的 network/transcoder/message-loader 后端由各自 `cmake/Xerces*Selection.cmake` 按优先级自动探测（取候选列表第 0 个）。默认探测结果在交叉编译下不够确定性，且可能拉入未发布依赖（R36）：

| 后端 | 候选优先级 | 默认风险 | 显式钉定 |
|------|-----------|---------|---------|
| network-accessor | curl → socket → winsock → cfurl | UNIX 上若 `find_package(CURL)` 命中（容器/worker 装了 libcurl）会选 curl，拉入未发布的 curl 依赖 | `socket`（原生 BSD socket + getaddrinfo，musl libc 内置） |
| transcoder | icu → gnuiconv → iconv → … | 若 `ICU_FOUND` 会选 icu，拉入未发布的 ICU 依赖 | `gnuiconv`（libc iconv：iconv_open/iconv/iconv_close，musl 内置） |
| message-loader | inmemory → icu → iconv | 默认即 inmemory（列表首项），但显式锁定避免被 ICU 探测覆盖 | `inmemory`（内置消息目录） |

ICU 本身非强制：`cmake/XercesICU.cmake` 仅 `find_package(ICU)`，且只在 `if(ICU_FOUND)` 时进入候选；缺失时静默忽略。但为避免 worker 上偶装 libcurl/ICU 导致探测漂移，三个后端一律显式钉到 libc-only 实现。

## pthread / iconv 依赖
- mutex-manager 默认 `standard`（C++ `std::thread`/`std::mutex`，由 `XercesMutexMgrSelection.cmake` 编译探测决定）；musl/libc++ 下 std::thread 底层走 pthread。
- musl 的 pthread、iconv、socket 符号**全部在 libc**，无独立 `libpthread`/`libiconv`/`libnsl`。因此静态库 `package_info` **不声明 system_libs**——链接时由 libc 自动解析。
- 若改为 glibc 目标才需 `-lpthread -ldl`，本目标仅 OHOS(musl) 故无需。

## 静态 vs 共享
- 默认 `BUILD_SHARED_LIBS=ON` 产 `libxerces-c-3.2.so.<ver>` + soname 软链（`cmake/XercesDLL.cmake`）。
- 本配方选**静态** `BUILD_SHARED_LIBS=OFF` 产 `libxerces-c.a`：
  - xerces-c 非系统同名库（R26 不强制静态），但静态产物最简单、依赖最少；
  - 规避 OHOS 共享库 SONAME/版本软链/签名链路（glfw 的 ML-0035/ML-0043）等已知 CI 失败面；
  - 与 marisa 等已合入库的"库类型默认静态"先例一致。

## 仅构建 xerces-c 目标
- 顶层 `CMakeLists.txt` 无条件 `add_subdirectory(tests)` / `add_subdirectory(samples)` 并 `enable_testing()`，**configure 阶段**会处理这些子目录（仅建目标、不安装）。
- 这些测试/示例可执行文件非本库产物，且其中部分需目标平台运行环境；为聚焦库产物、避免示例编译偶发问题拖累构建，`build()` 仅 `--target xerces-c`。
- 运行期 API 验证交由 `test_package/test.cpp`（XercesDOMParser 解析内存 XML + DOM 遍历断言）。

## 上游测试
- 上游有完整测试套件（`tests/src/`：DOMTest、DOMMemTest、XSValueTest、XSerializerTest 等）与示例（`samples/src/`：DOMCount、SAX2Print、XInclude 等），均链接 xerces-c。
- CMake 无 `build-tests` 开关；本配方未内建上游测试（交叉编译、需目标平台运行），改用 test_package 做消费者侧冒烟。

## 验证（本机构建容器）
- 容器内 `conan create` 通过：configure 选定 `transcoder=gnuiconv / network-accessor=socket / message-loader=inmemory`，静态库 `libxerces-c.a` 编译成功。
- test_package 编译链接通过；运行 `test_xerces` 输出 `OK (6/6 assertions)`。

## CI 超时修复
- CI 构建 #3275 在 `source()` 阶段超时（600 秒无输出），根因：CI worker 从 `archive.apache.org` 下载源码包缓慢。
- 修法：`conandata.yml` 的 `sources.url` 从单值改为列表，追加 `dlcdn.apache.org`、清华镜像、中科大镜像作为 fallback。
- 容器内验证通过（从 `archive.apache.org` 成功下载，构建+test_package 全部 OK）。

## 鸿蒙真机复测

- 日期：2026-07-19
- 环境：HarmonyOS HAD 206.1.0 真机（aarch64 musl，OHOS SDK clang 15.0.4）
- 结果：✅ 通过（conan create + test_package 真机原生执行）
