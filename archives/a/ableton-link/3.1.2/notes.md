# ableton-link 3.1.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-11
- 编译器: clang/clang++ (HarmonyOS PC aarch64)
- 状态: built

## 编译步骤

1. 拉取上游源码 `https://github.com/Ableton/link/archive/refs/tags/Link-3.1.2.tar.gz`（sha256 2673dfad…）
2. **额外拉取 asio-standalone**：GitHub source archive 不含 submodule 内容，`modules/asio-standalone/` 在 tarball 里是空目录。从 chriskohlhoff/asio 官方 tag `asio-1-30-2`（sha256 755bd7f8…）单独下载，解压到 `modules/asio-standalone/asio/include`，与上游 `AsioStandaloneConfig.cmake` 的预期路径一致。
3. 应用 3 个补丁（见 conandata.yml / patches/）：
   - `0001-CMakeLists.txt.patch`：新增 `LINK_BUILD_EXAMPLES` 选项并包裹 `add_subdirectory(examples)`
   - `0002-AbletonLinkConfig.cmake.patch`：Linux 平台匹配加入 `OHOS|HarmonyOS`；OHOS 下跳过 `atomic`/`pthread` 链接
   - `0003-ConfigureCompileFlags.cmake.patch`：去掉 Clang/GCC 分支的 `-Werror`
4. conan create 构建（OHOS profile）：
   - `CMAKE_SYSTEM_NAME=Linux`（E092：CMake 无 HarmonyOS 平台模块）
   - `LINK_BUILD_TESTS=ON`、`LINK_BUILD_EXAMPLES=OFF`、`LINK_OHOS=ON`
5. 上游测试：构建产物 `bin/LinkCoreTest` + `bin/LinkDiscoveryTest`（Catch2，25 个 TEST_CASE）在 build() 末尾真机执行，输出 `HMBS_UPSTREAM_TEST_RESULT` 标记。
6. test_package：`test_link.cpp` 调用真实 API（Link 构造 / enable / setTempo / SessionState 往返 / numPeers），经 ctest 运行并输出 `HMBS_TEST_PACKAGE_RESULT` 标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `modules/asio-standalone` 在源码包中为空 | GitHub source archive 不含 submodule 内容（.gitmodules 只声明 URL） | conandata.yml 增加 `asio:` 第二 source，source() 中单独下载 asio-1-30-2 解压到 `modules/asio-standalone/asio/include` |
| 2 | CMake 不识别 HarmonyOS 平台（E092） | CMake 没有 HarmonyOS platform module，`if(UNIX)` 与 `CMAKE_SYSTEM_NAME MATCHES "Linux…"` 分支不生效 | generate() 设 `CMAKE_SYSTEM_NAME=Linux`，让上游走 Linux 平台分支（linux Clock / posix ScanIpIfAddrs / stl Random），并定义 `LINK_PLATFORM_LINUX` |
| 3 | 上游 Clang 分支 `-Weverything -Werror` 编译风险 | bundled asio/catch 头在 OHOS clang 上产生警告会变错误 | 补丁去掉 `-Werror`（保留 -Weverything 只告警不报错） |
| 4 | examples（LinkHut）在 Linux 分支链接 PortAudio/asound | OHOS 无 portaudio/alsa 库，链接必失败 | 补丁新增 `LINK_BUILD_EXAMPLES` 开关，配方置 OFF |
| 5 | `AbletonLinkConfig.cmake` Linux 分支链接 `atomic pthread` | OHOS libc 自带 pthread 符号、aarch64 原生原子操作，`-latomic`/`-lpthread` 无对应库 | 补丁用 `LINK_OHOS` 变量守卫跳过这两个链接项 |
| 6 | 库为 header-only（`Ableton::Link` 是 IMPORTED INTERFACE，无 .so/.a） | 上游无 install 规则，conan create 无产物可装 | package() 直接 copy `include/ableton` + vendored asio 头 + LICENSE；package_info 声明 `LINK_PLATFORM_LINUX` 宏供 consumers |
| 7 | test_package 编译报 `fatal error: 'ableton/Link.hpp' file not found`（真机预检 2026-08-11） | Conan 2 的 `copy()` 用 fnmatch 按**文件**相对路径匹配，裸目录名 `"ableton"`/`"asio"` 匹配不到任何文件，头文件未打进包 | package() 改为通配符复制：`copy(self, "ableton/*", …)` 与 `copy(self, "*", asio_inc, …)`（保留目录结构） |

## 源码修改

- `patches/0001-CMakeLists.txt.patch` — 新增 `LINK_BUILD_EXAMPLES` 选项，包裹 `add_subdirectory(examples)`（默认 ON，配方 OFF）
- `patches/0002-AbletonLinkConfig.cmake.patch` — Linux 平台匹配加 `OHOS|HarmonyOS`；`if(NOT LINK_OHOS)` 守卫 atomic/pthread
- `patches/0003-ConfigureCompileFlags.cmake.patch` — 移除 Clang/GCC `-Werror`

## 依赖版本

- asio-standalone: 1.30.2（上游 Link 3.1.2 的 submodule 指向 chriskohlhoff/asio，官方 tag asio-1-30-2）
- catch: 上游 vendored（third_party/catch/catch.hpp，随源码包自带）
- 无其他外部 Conan 依赖

## 验证结果

```bash
# 真机预检（HarmonyOS PC aarch64，hmbs 执行）：
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 上游：bin/LinkCoreTest + bin/LinkDiscoveryTest（25 个 Catch2 TEST_CASE）
# test_package：ctest -R test_link（6 项 Link API 检查）
```

## 注意事项

- 本库是 header-only，但 consumers 编译时依赖 vendored asio 头 + `LINK_PLATFORM_LINUX` 宏，两者均已由配方 package()/package_info() 提供，无需额外声明依赖。
- 上游测试计数口径：LinkCoreTest 16 个 TEST_CASE（src/ableton/link/* + tst_Link.cpp）+ LinkDiscoveryTest 9 个 TEST_CASE（src/ableton/discovery/*），合计 25。
- 真机与命令属内部基建，仅记录于本笔记，不写入 PR 正文。
