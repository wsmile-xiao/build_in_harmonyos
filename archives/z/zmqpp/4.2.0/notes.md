# zmqpp 4.2.0 适配笔记

## 基本信息

- 上游仓库：<https://github.com/zeromq/zmqpp>
- 上游版本：4.2.0
- 构建系统：CMake
- 许可证：MPL-2.0
- Conan 依赖：`zeromq/4.3.5`
- 源码归档 SHA-256：`c1d4587df3562f73849d9e5f8c932ca7dcfc7d8bec31f62d7f35073ef81f4d29`

## W0 证据

- 设备源码下载、归档校验、语言预检、prescan 和 `zeromq/4.3.5` 依赖解析均已通过。
- 设备工具链为 Python 3.12.8、Conan 2.29.1、CMake 4.1.2、Clang 15.0.4。
- prescan 发现上游 Makefile 使用 `ln -sf`，以及 `publish_doc.sh` 使用 `/bin/bash`；本配方采用 CMake，不调用该 Makefile 或文档发布脚本。

## 适配内容

- 通过 `CMakeDeps` 使用 Conan 的 ZeroMQ CMake target。
- 关闭上游 examples、client 和 Boost 测试目标，默认构建静态 `libzmqpp`。
- 以四个小补丁补充现代 CMake 项目声明、C++11 target 特性、缺失头文件、`_WIN32` 预处理判断，并修复上游测试在 HarmonyOS 上的参数和 monitor endpoint。

## 设备验证

- 本轮设备验证对应实现提交 `637c45264dac24dfcf28fa665a68c7989eeac7fc`，并在设备任务 worktree `/storage/Users/currentUser/ws/wt-zmqpp-4.2.0-r2` 核对本地与设备 SHA 一致；随后提交 `378a0d2e808592319f4afb94a544700cc2720620` 仅修正测试统计清单和说明，未改配方、补丁或测试逻辑，因此设备验证仍以 `637c45264d` 的实现为准。W3 过程会在包目录生成临时代理版 `conandata.yml` 和 `.build-cache`，已将它们移入任务私有临时目录并恢复 tracked 文件，最终 `git status --short` 为空。
- 源码归档 SHA-256：`c1d4587df3562f73849d9e5f8c932ca7dcfc7d8bec31f62d7f35073ef81f4d29`；四个补丁均应用成功，无 `.rej`。
- 原生 CMake：设备 Clang 15.0.4、CMake 4.1.2、Ninja；Release 静态库 configure/build/install 成功，Ninja 构建 `33/33`，安装到任务私有 prefix，未写入系统目录。
- 上游测试命令：`ctest --test-dir upstream-build --output-on-failure -j1` 与 `./zmqpp-test-runner --log_level=test_suite`。源码清点命令为 `grep -h -o -E 'BOOST_AUTO_TEST_CASE[[:space:]]*\(' zmqpp-4.2.0/src/tests/*.cpp | wc -l`，15 个上游测试源文件共注册 `118` 个 case；其中 `test_load.cpp::load/push_messages_baseline`、`test_load.cpp::load/push_messages` 位于 `#ifdef LOADTEST` 下，`test_socket.cpp::sending_large_messages_string` 位于 `#ifndef TRAVIS_CI_BUILD` 下，而上游 CMake 默认定义 `TRAVIS_CI_BUILD`，因此这 3 个源码注册项默认未编译。最终 runner 实际注册 `115` 个 case，`TOTAL=115 = PASS=112 + FAIL=0 + SKIP=3 + NOT_RUN=0`；三个 skip 为 `auth/stonehouse`、`auth/ironhouse`、`auth/ironhouse2`，均由 ZeroMQ 未启用 libsodium 的上游条件触发；CTest 和 runner 退出码均为 0。
- Conan 最终采信轮使用任务私有 `CONAN_HOME`，只恢复已验证的 `zeromq/4.3.5` 二进制依赖，zmqpp 自身 source/build/package 从空缓存生成；完整 package reference 和逐项制品核对记录在本轮验证证据中，G0/G1/G2/G3/G4 及 L2/L4/L5 均按实际结果记录。
- Conan 工具报告的 G4/L2/L4/L5 因 package ID 解析缺陷显示为“跳过”；未将该假绿直接采信。人工 supplement 已按完整 package reference 核对：24 个 `.hpp`、1 个导出头、1 个静态库、1 个许可证；`test_package` 二进制与 CTest 均通过；静态库 16 个成员全部为 AArch64 ELF64 `REL` 对象，无可加载 ELF，NX/PIE/RELRO 对该静态归档不适用；包文件 SHA-256 基线已留证。
- Conan `test_package` 单独统计为 1 个 HarmonyOS 消费者用例，真实编译并运行 `test_zmqpp`，输出 `zmqpp version and inproc round trip passed`；该消费者覆盖 CMake target `zmqpp::zmqpp`、版本 API 和 inproc PUSH/PULL 链路，未执行动态加载，因为发布物是静态库；它不混入上游 `118` 个源码注册项或 runner `115` 个 case。
- W3 `setup.sh` 和 `build_and_test.sh archives/z/zmqpp/4.2.0` 在显式提交绑定下通过，准确时间、SHA 和清理前后状态以最终 SHA 对应的 W3 原始日志为准：L0、L1、L4、L5 为 pass；L2 因库包无 `bin/` 为不适用 skip；test_package 真实运行，目标包构建成功。
- `finish ... built` 的真实 W3 通过，但总退出码为 1：G0 原始 tarball 预检、submit-only 遗留 packaging/test-report/staging 项和仓库存量 W5 字段/草稿产生警告；归档已关闭为 `built`。finish 生成的镜像版 `conandata.yml`、截断 `SUMMARY.md`、`.build-cache` 和备份文件均已审查并恢复/删除，未进入提交。

## 修复记录

- 初次 Conan G2 失败的真实原因是 `0001-fix-cmake.patch` 使第四个补丁的 CMake hunk 向后移动 16 行，而设备 Conan 补丁实现不搜索偏移；将 `0004` 的 hunk 从 `223` 对齐到前三个补丁后的 `239` 后，空缓存目标包构建通过。
