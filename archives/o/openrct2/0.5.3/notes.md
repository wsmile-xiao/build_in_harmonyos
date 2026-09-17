# openrct2 0.5.3 适配笔记

## 形态决策：headless 服务器

**为什么不是全量 GUI**：
1. 仓内 sdl2/2.30.10 定制版（OHOS 专用 patch）：视频后端仅 `SDL_VIDEO_DRIVER_DUMMY` +
   `SDL_VIDEO_DRIVER_OFFSCREEN`，无 X11/Wayland/Android 后端——GUI 可编译但运行时无真实渲染。
2. 音频层依赖冲突：flac/1.4.3 → libogg/1.3.5，libvorbis/1.3.7 → libogg/1.3.6，
   conan 图冲突无法共解（都在 openrct2-ui 层）。
3. openrct2 官方支持 headless 服务器形态（`openrct2-cli --headless` + `host <park>` 命令），
   在无显示环境的服务器场景是核心用法（多方联机服务器）。

因此 conanfile 用 `DISABLE_GUI=ON`：产物 = `bin/openrct2-cli`（含 libopenrct2 静态库、
headless 命令行、服务器功能）+ `share/openrct2/` 数据文件（language/shaders 等）。

## 依赖集成（核心 patch）

上游 `src/openrct2/CMakeLists.txt` 用 `PKG_CHECK_MODULES`（pkg-config）查找
libcurl/fontconfig/freetype/libzip/zlib/zstd/libpng/ICU，用 `find_package(OpenSSL 1.0.0)` /
`find_package(ICU 59.0 COMPONENTS uc)`。CI/conan 环境无系统 pkg-config 数据——
patch 全部改写为 CMakeDeps 生成的 find_package + target：

| 上游 | conan/CMakeDeps |
|---|---|
| `find_package(OpenSSL 1.0.0)` + `${OPENSSL_LIBRARIES}` | `find_package(openssl)` + `openssl::openssl` |
| `PKG_CHECK_MODULES(LIBCURL ...)` | `find_package(CURL)` + `CURL::libcurl` |
| `PKG_CHECK_MODULES(FONTCONFIG ...)` | `find_package(fontconfig)` + `fontconfig::fontconfig` |
| `PKG_CHECK_MODULES(FREETYPE ...)` | `find_package(freetype)` + `freetype::freetype` |
| `PKG_CHECK_MODULES(LIBZIP/ZLIB/ZSTD/PNG)` | `find_package(libzip/ZLIB/zstd/libpng)` + 对应 target |
| `find_package(ICU 59.0 COMPONENTS uc)` | `find_package(icu4c)` + `icu4c::icu4c` |

## CMake 选项

- `DISABLE_GUI=ON` — headless（不建 openrct2 主程序，只建 openrct2-cli + libopenrct2）
- `DISABLE_DISCORD_RPC=ON` — DiscordRPC 制品仓无
- `DOWNLOAD_* = OFF` — title sequences/objects/opensfx/openmusic/replays 均为运行时
  可下载资源（assets.json 声明 URL+sha256），离线打包不内嵌；玩家首次运行时按需获取。
  conan 打包只带源码树内 `data/`（language、scenario_patches、shaders——编译期必需）。
- g2.dat 等 sprite 资源由构建机 openrct2-cli 生成（本机即 OHOS arm64，native 生成）
  ——非交叉编译路径 `if (NOT CMAKE_CROSSCOMPILING)` 走到。

## OHOS 特有处理

- make -j1（HMDFS 禁 mkfifo jobserver，全仓惯例）
- 平台文件 `Platform.Linux.cpp` 条件 `defined(__unix__) && !__ANDROID__ && !__APPLE__`
  ——OHOS（linux-ohos/musl）满足 __unix__，走 Linux 路径，已验证（getpwuid 等）。
- `dl` 系统库链接（UNIX && !BSD 分支已覆盖）

## 已知限制（如实申报）

- GUI 主程序（openrct2 桌面版）不在本配方产物中（上述 1/2 理由）
- 多人联机服务器需 assets（objects/title sequences），运行时从 GitHub 下载
  （assets.json 内置 URL+sha256 校验）
- 上游 test/tests 需 CI 夹具（replays 数据 + GTest），本地打包按 headless
  `openrct2-cli --version` 验证（test_package）


## C++20 / OHOS clang15(libc++15) 兼容修复清单（构建期实证）

工具链：clang 15.0.4（OHOS SDK 26.0.0.18），libc++ 15，-std=c++20。

| 现象 | 根因 | patch |
|---|---|---|
| nlohmann/json_fwd.hpp not found | 上游假设系统预装 nlohmann json，无 find_package | 0001 补 find_package(nlohmann_json) + 链接 |
| nlohmann 3.12 char8_t/u8string 报错 | 项目全局 -fno-char8_t 与 3.12 冲突 | requires 用 nlohmann-json/3.11.2（兼容 -fno-char8_t） |
| <stop_token> not found | libc++15 无 C++20 stop_token；该 include 在 BackgroundWorker.hpp 中未实际使用（代码用自实现 atomic_bool） | 0003 删除多余 include |
| 7+ 处 missing 'typename' | clang15 对 P0634（省略 typename）支持不完整 | 0003/0004/0005/0006/0009/0014/0015 补 typename |
| <source_location> not found | libc++15 无；Guard.hpp/cpp 实际使用 source_location::current() | 0007/0008 polyfill（__builtin_FILE/LINE/FUNCTION，clang9+ 可用） |
| make_unique_for_overwrite | C++23 特性 | 0010/0011 → make_unique（行为差异仅为不零初始化，游戏场景安全） |
| std::ranges::fill/lower_bound | libc++15 ranges 算法不完整 | 0012/0013 → std::fill/std::lower_bound 等价改写 |
| HookValuesToJS CTAD 失败 | 聚合 CTAD（P1816）clang15 未实现 | 0016 显式推导指引 |
| ExtensionCallbacks emplace_back 失败 | libc++15 construct_at 不支持 C++20 聚合括号初始化 | 0017 显式构造函数 |
| basic_ostringstream 未定义 | 缺 <sstream>（libc++15 传递包含更严格） | 0018/0019 补 include |
| install 阶段 g2.dat 缺失 | install(FILES g2.dat) 无条件，但 DISABLE_GUI 不生成 | 0002 install 规则加 NOT DISABLE_GUI 守卫 |

## test_package 环境坑（#9606 同族）

- env="conanrun" 单独用 → libc++_shared.so 找不到（Error relocating 127）：
  conanrun 不含工具链 llvm/lib 路径
- env="conanbuild" 单独用 → 依赖 .so（libcurl/libpng 等）找不到：
  conanbuild 不含依赖包 libdirs
- **正确做法：env=["conanbuild", "conanrun"] 组合**——两边 LD_LIBRARY_PATH 合并

## 本地验证记录（2026-09-12）

```
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
→ openrct2/0.5.3: Package 'a53db40560517895afe33cb98682047db29f6519' built ✅
→ test_package: openrct2-cli --version 输出：
   OpenRCT2, v0.5.3
   Linux (AArch64)
   Network version: 0.5.3-0
   Plugin API version: 115
   Current park file version: 61
   Minimum park file version: 57
   Breakpad support disabled ✅
```

构建耗时：make -j1 约 50 分钟（62946 文件 checkout，1347 个 .cpp/.h 编译单元）。

额外功能实测：`openrct2-cli sprite build g2.dat resources/g2/sprites.json silent`
→ exit 0，生成 g2.dat 169367 字节（sprite 工具链端到端验证）。


## CI 修复记录（PR #9656）

### 第一轮 CI（#44768）失败 → 根因

test_package 运行时 `Error loading shared library .../libexpat.so`——
**fontconfig/2.18.1 制品仓包缺陷**：其 libfontconfig.so.1 的 DT_NEEDED 是
绝对路径（指向 fontconfig 构建机的 expat 位置
`/storage/.../.conan2/p/expat9fb.../p/lib/libexpat.so`），在 CI worker
（conan home 为 .cache/conan2）上该路径不存在 → 加载失败。

实测对比（readelf -d）：
- fontconfig/2.18.1: NEEDED `/storage/.../libexpat.so`（绝对路径，坏）
- fontconfig/2.18.1.1: NEEDED `libexpat.so.1`（soname，LD_LIBRARY_PATH 可解析）
- fontconfig/2.18.3: 无 expat NEEDED（静态链）

### 修复（commit 81c3ee65c）

requires 从 fontconfig/2.18.1 → fontconfig/2.18.1.1（soname 链接）。
test() 用 `env=["conanbuild", "conanrun"]` 组合：
- conanbuild 提供工具链 llvm lib（libc++_shared.so）
- conanrun 提供依赖 lib dirs（含 expat）

### 第二轮 CI（#44776）✅ PASSED

2026-09-12 04:39，worker OpenHarmonyPCDeveloper-CI-020，校验通过。

### 教训沉淀

test_package 运行动态链接的 application 时，若报「Error loading shared
library <传递依赖>」，先 readelf -d 查 DT_NEEDED 是否为绝对路径——
制品仓中存在绝对路径 NEEDED 的坏包（构建时未用 -l<name> 而是 full path），
换同版本修复版（如 2.18.1.1）或上游版本。

## 上游测试真实执行（rule4 硬条款修复，2026-09-13）

人工审核（bengbeng2345 09-13 14:38）rule4 FAIL：上游 222 用例 0 测不通过，
新口径下必须真实执行。本节记录修复过程。

### 测试系结构

- `WITH_TESTS` CMake 选项 → `test/tests/`（30 个测试源文件，静态宏计数 222；
  运行时 TEST_P 参数化展开 274 用例/34 套件）
- 单目标 `OpenRCT2Tests`：`find_package(GTest REQUIRED)` + `GTest::gtest` +
  `gtest_discover_tests(DISCOVERY_MODE PRE_TEST)`
- 全部 headless 模式（gOpenRCT2Headless），无 GUI 依赖——headless 形态适配下
  无测试文件需要修改

### 依赖解决

- GTest：仓内 `gtest/1.17.0.1`（cmake_file_name=GTest，与上游
  find_package(GTest) 原生匹配）。本地 conan 缓存与 ohpcd 远端均有 OHOS
  arm64 二进制（pkgid 21b17f8b2bc0e9511e276e3d57a23893067cefe5）。
- 接法：`requirements()` 中 `self.tool_requires("gtest/1.17.0.1", visible=True)`
  + `generate()` 中 `deps.build_context_activated = ["gtest"]`——
  CMakeDeps 默认不给 tool_requires 生成 config 文件（cmakedeps.py 过滤
  `require.build and name not in build_context_activated`），激活后生成
  GTestConfig.cmake。tool_requires 不进包依赖图（pkgid/包内容不变）。
- 属性式 `tool_requires = ("gtest/...",)` 不支持 visible 参数，必须方法式。

### 测试资产（关键坑，3 轮迭代）

| 资产 | URL（assets.json） | 作用 | 缺失症状 |
|------|--------------------|------|----------|
| replays.zip v0.0.95 | OpenRCT2/replays release | ReplayTests TEST_P 19 实例 | 用例数为 0（目录扫描空） |
| objects.zip v1.7.10 | OpenRCT2/objects release | sv6/park 加载的 rct1/rct2/official objects | `Unable to open park: missing objects` → MapGetFootpathElement 返回 null → MapEdge 用例 segfault |
| openmusic.zip v1.6.1 | OpenRCT2/OpenMusic release | openrct2.music.* 音乐 object（EverythingPark.park 引用） | RideRatings.EverythingPark 失败（RideGetCount 0 ≠ 529） |

三个 zip 的 URL+sha256 都在源码树 assets.json，与上游 CI 同源。上游 CI 通过
CMake install 期下载（DOWNLOAD_* 选项 + DESTDIR 语义）；conan 离线流程改为
配方 source/build 期 `download(sha256=)` 校验 + 解压：
- replays → source() 放 `test/tests/testdata/replays/`（上游 CMakeLists 的
  `file(CREATE_LINK testdata)` 符号链接自动带入 build 目录）
- objects/openmusic → build() 组装 `$BUILD/openrct2-test-data/object/`
  （openmusic zip 只取 object/ 部分，assetpack 不需要）

### 数据目录契约（测试运行时）

- `$BUILD/testdata`：configure 期符号链接（tests/CMakeLists 的
  file(CREATE_LINK ... SYMBOLIC)，HMDFS 支持符号链接）
- `$BUILD/data`：Platform.Linux GetInstallPath 搜索 {exeDir,cwd}/data。
  测试二进制 cwd=$BUILD，链接到 openrct2-test-data（language ← 源码
  data/language 符号链接 + object/ 解压内容）

### ctest 运行环境

- `self.run(ctest..., env=["conanbuild", "conanrun"])`：conanbuild 提供
  工具链 llvm lib（libc++_shared.so），conanrun 提供依赖包 libdirs
  （libcurl/libpng/freetype/expat 等 .so）。单用任一都会缺库（#9606 同族）。
- ctest 逐用例独立进程执行：`100% tests passed, 0 tests failed out of 274`，
  总耗时 72s；直跑 OpenRCT2Tests 23.5s。

### 最终结果

274/274 通过（0 失败 0 跳过 0 环境不可跑项），34 套件分布与逐用例输出见
reports/test-report.md 与 reports/conan-create-tests.log。
