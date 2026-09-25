# csfml 3.0.0 OpenHarmony PC 适配笔记

## 适配范围

交付 CSFML 3.0.0 的 C 绑定 `System` 与 `Network` 两个模块：

- `libcsfml-system.so.3.0.0`（SONAME `libcsfml-system.so.3.0`）
- `libcsfml-network.so.3.0.0`（SONAME `libcsfml-network.so.3.0`）
- `include/CSFML/{System,Network}/**.h` 共 24 个头文件

`Window`、`Graphics`、`Audio` 与已合入的 `archives/s/sfml/2.6.1.1`、`archives/c/csfml/2.6.0`
口径一致，本次不纳入：`Window` 需要 EGL/GLES 或 X11 窗口后端，`Graphics` 依赖 `Window` +
FreeType，`Audio` 需要 OpenAL 设备与已发布的 OpenAL 包，OHOS PC 的 CI 镜像都不具备。
`package()` 会裁掉 `include/CSFML/{Window,Graphics,Audio}` 与对应伞形头，
以及 `GPUPreference.h`、`OpenGL.h`（`System`/`Network` 的任何头文件都不 include 它们，已核对）。

## 依赖处理：为什么这里没有 `requires = "sfml/3.0.0"`

- CSFML 3.0.0 的 `CMakeLists.txt` 写死 `find_package(SFML 3.0 COMPONENTS ...)`，2.6 的 CMake 配置既不满足版本，
  C++ API 也不兼容（`sf::Time`/`sf::Event`/`sf::Err` 在 3.0 是重写过的）。
- 制品仓当前只有 `sfml/2.6.1` 与 `sfml/2.6.1.1`
  （`GET https://ohpcd.atomgit.com/api/registry?keyword=sfml` 实测 `total=2`），
  而 CI 门禁 L0i/R36 要求声明的依赖必须先发布到制品仓 —— 写 `sfml/3.0.0` 会直接判红。

因此本配方把 SFML 3.0.0 官方 release 当作**构建期输入**而不是运行期依赖：

1. `source()` 下载三个官方 tarball（全部 `https://codeload.github.com/...` + `sha256`，
   因 codeload URL 末段是 tag 名，`get()` 一律显式给 `filename=`，否则会按 ZIP 解析报 `BadZipFile`）：
   CSFML 3.0.0、SFML 3.0.0、Catch2 3.7.0。
2. `build()` 先把 SFML 的 `System`+`Network` 以 `BUILD_SHARED_LIBS=OFF` +
   `CMAKE_POSITION_INDEPENDENT_CODE=ON` 编成静态库，安装进构建目录内的私有 prefix。
3. 再以 `CSFML_LINK_SFML_STATICALLY=ON` 编 CSFML，SFML 代码直接链入 `libcsfml-*.so`。

结果：包内**不含**任何 SFML 库、SFML 头文件或 CMake target，`requires` 为空，
不引入未发布依赖。实测两个产物的 `DT_NEEDED` 只有 `libc++_shared.so` 与 `libc.so`。

已知代价：SFML 上游升级需要同步本配方；制品仓一旦发布 `sfml/3.0.x`，
应改回 `requires("sfml/3.0.x")` 并删掉 `bundled/` 那一段（`conandata.yml` 已就地注明原因）。

## 构建方式

构建系统 CMake（CSFML 要求 ≥3.22，本环境 CMake 4.4.3）。关键选项：

```text
BUILD_SHARED_LIBS=ON            # 与 default_options.shared=True 一致
CSFML_BUILD_WINDOW=OFF
CSFML_BUILD_GRAPHICS=OFF
CSFML_BUILD_AUDIO=OFF
CSFML_BUILD_NETWORK=ON
CSFML_LINK_SFML_STATICALLY=ON
CSFML_BUILD_TEST_SUITE=ON
CSFML_BUILD_DOC=OFF
CSFML_BUILD_EXAMPLES=OFF
CSFML_INSTALL_PKGCONFIG_FILES=OFF
FETCHCONTENT_SOURCE_DIR_CATCH2=<source>/bundled/catch2-src
SFML_DIR=<build>/bundled-sfml/lib/cmake/SFML
```

OHOS 专属处理（与 `archives/c/csfml/2.6.0` 同根因）：

- `CMAKE_SHARED_LINKER_FLAGS=-Wl,--enable-new-dtags`：RPATH 降级 RUNPATH，让 `conanrun` 的
  `LD_LIBRARY_PATH` 优先。
- `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,`：CMake 没有 `Platform/HarmonyOS`，
  不显式补就会编出无 DT_SONAME 的共享库，撞上 L5a 门禁。

## 补丁说明

- `0001-cmake-Config.cmake-recognize-harmonyos.patch`：让 CSFML 的平台检测把 `HarmonyOS`
  当作 Linux 分支（OHOS SDK 目标三元组是 `aarch64-unknown-linux-ohos`）。
- `0002-test-CMakeLists-gate-disabled-modules.patch`：
  ① 把 Catch2 编成静态库 —— `BUILD_SHARED_LIBS=ON` 会连带把 Catch2 也编成 `.so`，
  而它落在 `_deps/` 里、不在 `LIBRARY_OUTPUT_PATH` 下，测试可执行文件在发现阶段就 127；
  ② `test-csfml-{window,graphics,audio}` 三个套件按 `CSFML_BUILD_*` 开关 gate 掉，
  否则 `target_link_libraries` 找不到 `SFML::Window` 等 imported target，configure 直接失败。
- `0003-bundled-sfml-cmake-Config.cmake-recognize-harmonyos.patch`：同样的平台识别补丁，
  作用在 `bundled/sfml-src/` 上。

## 测试

上游官方套件（CSFML 3.0 起自带 Catch2 测试集，2.6 时代没有）：

- 取数：`grep -rEc '^[[:space:]]*TEST_CASE' test/*/*.test.cpp` → 全量 **29** 个 `TEST_CASE`。
- 本次交付模块：**10** 个（`System` 6 + `Network` 4），`catch_discover_tests` 逐个注册成 ctest 用例，
  真机实测 `100% tests passed out of 10`。
- 未运行 19 个：`Window` 6 / `Graphics` 12 / `Audio` 1，全部属于本包关闭的模块，
  逐条原因写在 `test_package/MANIFEST.yml`。
- `build()` 里跑测试必须自带 `LD_LIBRARY_PATH=<build>/lib`：
  `ctest` 的 PRE_TEST 发现模式要真的执行测试二进制，OHOS 加载器不认 CMake 的 build-tree RPATH。

`test_package` 是消费者视角的纯 C 程序（`find_package(CSFML)` + `csfml-system`/`csfml-network`），
24 条 `CHECK()` 覆盖时钟、Time 换算、包序列化、IP 地址转换，真机 `24/24 passed`。

## Verification status

真机 OpenHarmony PC aarch64（clang 15.0.4 / OHOS SDK 26.0.0.18 native llvm，
profile `~/.conan2/profiles/ohos-aarch64`，`CONAN_HOME=~/work/psj/ch-csfml`，
任务 #6921，2026-09-21 起）：

```bash
conan create archives/c/csfml/3.0.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

- `CREATE_EXIT:0`
- 上游 ctest：`1/10`…`10/10` 全 Passed，`100% tests passed out of 10`，`Total Test time (real) = 1.04 sec`
- `test_package`：`csfml consumer checks: 24/24 passed`
- 包引用：`csfml/3.0.0#ecaf1a76138ba8682f638878858c9149:01d92cf349a0dd98ff915f4bd99a04430171517f#3fb07996cff9e9de50f4f202eb579bb4`
- 产物：`lib/libcsfml-system.so.3.0.0` 22848 B
  （sha256 `44f538f3af7ce0c99a1010d2acab5bfe081558e48bff410efafdbdd046bd4acb`）、
  `lib/libcsfml-network.so.3.0.0` 211392 B
  （sha256 `b1a159eb3ac8ed22721b9c00355cb4cd6ab3289564e253bf23bac2f04cdec7c6`）、
  24 个头文件、`licenses/license.md`、`share/CSFML/{license,readme}.md`；**无 `bin/`**
- ELF：两个产物的 `DT_NEEDED` 只有 `libc++_shared.so`、`libc.so`（无绝对路径），`DT_SONAME` 正常
- ELF 签名：`/data/service/hnp/bin/binary-sign-tool` 在本机不存在（只有 CI worker 有），
  `_sign_shared_libs()` 按 p11-kit 的做法 warning 后跳过；本机实测未签名的 `.so` 直接可装载运行
  （`env LD_LIBRARY_PATH=<pkg>/lib ./sigprobe` → `ELAPSED_OK`）。CI worker 上该函数会真签名。
