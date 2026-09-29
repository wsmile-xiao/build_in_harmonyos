# logfault 0.8.5 上游测试逐入口台账（R03 全量补齐后）

来源树：`tests/`（官方 tag v0.8.5 tarball，sha256 0cb8b83e...）
编译环境：clang 15.0.4 (aarch64-unknown-linux-ohos)；gtest 1.14.0（C++14 档）/ gtest 1.12.1（C++11 档，均设备侧构建）
依赖补齐（R03）：libboost_json.a（缓存 boost 头文件 + src.hpp 设备侧构建）、libsystemd.so.0（conan systemd/261，ohpcd registry 预编译 armv8）

## 逐入口台账（N=26 全量可运行）

| # | 入口（相对 tests/） | TEST 宏数 | 编译标准 | 构建退出码 | 运行退出码 | 结果 | 归类 |
|---|--------------------|----------|----------|-----------|-----------|------|------|
| 1 | cxx11/logfault_cxx11_tests.cpp | 2 | c++14（上游 logfault.h 需 C++14 auto-lambda；gtest 1.12.1 支持 C++11） | 0 | 0 | `[ PASSED ] 2 tests` | 可运行且已运行 |
| 2 | cxx14/logfault_cxx14_tests.cpp | 2 | c++14（gtest 1.14.0） | 0 | 0 | `[ PASSED ] 2 tests` | 可运行且已运行 |
| 3 | cxx17/logfault_cxx17_tests.cpp | 2 | c++17 | 0 | 0 | `[ PASSED ] 2 tests` | 可运行且已运行 |
| 4 | cxx20/logfault_cxx20_tests.cpp | 2 | c++20 | 0 | 0 | `[ PASSED ] 2 tests` | 可运行且已运行 |
| 5 | cxx23/logfault_cxx23_tests.cpp | 2 | c++2b | 0 | 0 | `[ PASSED ] 2 tests` | 可运行且已运行 |
| 6 | default_to_clog.cpp | 6（Linux 生效） | c++17 | 0 | 0 | `[ PASSED ] 6 tests` | 可运行且已运行 |
| 7 | json_escape_tests.cpp | 8 | c++17 | 0 | 0 | `[ PASSED ] 8 tests` | 可运行且已运行 |
| 8 | json_tests.cpp | 3 | c++17 + libboost_json.a | 0 | 0 | `[ PASSED ] 3 tests` | 可运行且已运行 |
| 9 | systemd_tests.cpp | 2 | c++17 + libsystemd | 0 | 0 | `[ PASSED ] 2 tests` | 可运行且已运行 |
| 10 | os_log_tests.cpp | 1 | c++17 | 1 | - | `os/log.h file not found`（仅 Darwin 注册） | 不可运行（平台非 Darwin） |
| 11 | general_tests.cpp | 0 | - | - | - | 未注册进 tests/CMakeLists.txt | 不可运行（上游未注册） |
| 12 | CMakeLists.txt（根） | - | - | - | - | 注册清单 | 构建脚本 |

## 统计口径（R03）

- **上游可运行入口实际执行：cxx11 2 + cxx14 2 + cxx17 2 + cxx20 2 + cxx23 2 + clog 6 + json_escape 8 + json_tests 3 + systemd 2 = 29 用例，29/29 通过（100%）**
- 审查口径说明：赛事审查 N=26 指补齐 cxx11/cxx14（4 例）后 R02 声明 22 例增至 26 例（cxx11-23 10 + clog 6 + json_escape 8 + systemd 2）；本轮另补齐 libboost_json 使 json_tests 3 例实跑通过，实际执行合计 29 例全通过（100%），无少报
- 不可运行：os_log_tests（仅 Darwin，OHOS 无 Apple os framework）、general_tests（上游未注册）——单列，不计入适配后合计与通过率分母
- json_tests 需 libboost_json 编译库（R03 设备侧构建）；systemd 实连需 libsystemd.so.0（R03 conan systemd/261 取得）

## 依赖来源记录

| 依赖 | 来源 | 版本 | 绝对路径 |
|------|------|------|----------|
| gtest（C++14 档） | GitHub release-1.14.0 tarball 设备侧构建 | 1.14.0 | /storage/Users/currentUser/tmp/logfault-r03-deps/prefix |
| gtest（C++11 档） | GitHub release-1.12.1 tarball 设备侧构建 | 1.12.1 | /storage/Users/currentUser/tmp/logfault-r03-deps/prefix12 |
| libboost_json.a | 缓存 boost 头文件 + boost/json/src.hpp 编译 | boost 1.84.0 头 | /storage/Users/currentUser/tmp/logfault-r03-deps/boostjson |
| libsystemd | conan ohpcd systemd/261（预编译 armv8） | 261 | /storage/Users/currentUser/.conan2/p/syste863f74a3ae4d6/p |

> 依赖产物全部位于设备侧临时/缓存目录，未写入当前库 diff、staged、commit 或 PR。
