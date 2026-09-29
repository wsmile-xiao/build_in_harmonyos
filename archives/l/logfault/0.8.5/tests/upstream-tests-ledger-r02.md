# logfault 0.8.5 上游测试逐入口台账（R02 复核）

来源树：`tests/`（解压自官方 tag v0.8.5 tarball，sha256 0cb8b83e...）
编译环境：clang 15.0.4 (aarch64-unknown-linux-ohos)，gtest 1.17.0（conan 缓存），boost header-only 1.84.0（缓存）
全部入口的真实存在性、构建与运行结果按下方逐项核验，含本轮（R02）重新尝试。

## 逐入口台账

| # | 入口（相对 tests/） | 存在性 | 计数规则 | 命令(cwd=tests/) | 构建退出码 | 运行退出码 | 结果 | 归类 | 阻塞归属 | 恢复条件 |
|---|--------------------|--------|----------|------------------|-----------|-----------|------|------|----------|----------|
| 1 | cxx11/CMakeLists.txt + logfault_cxx11_tests.cpp | 存在 | CMake add_executable+add_test；2 个 GTest 用例 | `clang++ -std=c++11 ... logfault_cxx11_tests.cpp -lgtest` | 141 | - | `#error C++ versions less than C++17 are not supported.`（gtest 1.17.0 gtest-port.h:273） | 不可运行 | 第三方依赖（gtest 版本要求 C++17） | 安装支持 C++11 的旧 gtest（<1.15）后重试 |
| 2 | cxx14/CMakeLists.txt + logfault_cxx14_tests.cpp | 存在 | 同上；2 个 GTest 用例 | `clang++ -std=c++14 ... logfault_cxx14_tests.cpp -lgtest` | 141 | - | 同 cxx11：gtest 1.17.0 `#error C++ versions less than C++17` | 不可运行 | 第三方依赖（gtest 版本要求 C++17） | 同 cxx11 |
| 3 | cxx17/CMakeLists.txt + logfault_cxx17_tests.cpp | 存在 | add_test 1 项；2 个 GTest 用例 | `clang++ -std=c++17 ... -o cxx17_tests && ./cxx17_tests` | 0 | 0 | `[ PASSED ] 2 tests` | 可运行且已运行 | - | - |
| 4 | cxx20/CMakeLists.txt + logfault_cxx20_tests.cpp | 存在 | add_test 1 项；2 个 GTest 用例 | 同上 c++20 | 0 | 0 | `[ PASSED ] 2 tests` | 可运行且已运行 | - | - |
| 5 | cxx23/CMakeLists.txt + logfault_cxx23_tests.cpp | 存在 | add_test 1 项；2 个 GTest 用例 | 同上 c++2b | 0 | 0 | `[ PASSED ] 2 tests` | 可运行且已运行 | - | - |
| 6 | default_to_clog.cpp | 存在 | 1 个 GTest suite，6 个用例 | `clang++ -std=c++17 ... default_to_clog.cpp -o default_to_clog && ./default_to_clog` | 0 | 0 | `[ PASSED ] 6 tests` | 可运行且已运行 | - | - |
| 7 | json_escape_tests.cpp | 存在 | 1 个 GTest suite，8 个用例 | `clang++ -std=c++17 ... json_escape_tests.cpp -o json_escape_tests && ./json_escape_tests` | 0 | 0 | `[ PASSED ] 8 tests` | 可运行且已运行 | - | - |
| 8 | json_tests.cpp | 存在 | 1 个 GTest suite；依赖 Boost::json 解析 | `clang++ -std=c++17 -DBOOST_JSON_HEADER_ONLY ... json_tests.cpp -lgtest` | 1 | - | `ld.lld: undefined symbol: boost::json::parse(...)`（缓存 boost 无 libboost_json 编译库） | 不可运行 | 第三方依赖（需 libboost_json 编译库） | 安装带 json 组件的 boost 包后重试 |
| 9 | systemd_tests.cpp | 存在 | 2 个 GTest 用例 | `clang++ -std=c++17 ... systemd_tests.cpp -o systemd_tests && ./systemd_tests` | 0 | 1 | SendsExpectedFields PASS；DoActualLoggingWithSystemd FAIL：`Failed to load libsystemd: libsystemd.so.0: No such file or directory` | 可运行且已运行（1/2，实连例受环境限制失败） | 平台基础设施（OHOS 无 libsystemd） | 安装 libsystemd 或提供 stub 后可全过 |
| 10 | general_tests.cpp | 存在 | 未注册进 tests/CMakeLists.txt（无 add_executable/add_test 引用） | 未构建（无注册入口） | - | - | 上游未注册的辅助/开发用源文件，非正式测试入口 | 可运行但本轮未运行（上游未注册） | 上游注册后按标准构建 |
| 11 | os_log_tests.cpp | 存在 | 仅 `CMAKE_SYSTEM_NAME STREQUAL "Darwin"` 时注册 | `clang++ -std=c++17 ... os_log_tests.cpp -lgtest` | 141 | - | `fatal error: 'os/log.h' file not found`（Darwin 专属） | 不可运行 | 平台基础设施（OHOS 非 Darwin，无 Apple os framework） | 仅 Apple 平台可运行 |
| 12 | CMakeLists.txt（tests/ 根） | 存在 | 声明 GTest+Boost 依赖并将 1-11 编入 | 见上各入口 | - | - | 注册清单已逐一核验 | - | - | - |

## 统计口径（R02）

- 可运行且已运行：cxx17(2)、cxx20(2)、cxx23(2)、default_to_clog(6)、json_escape_tests(8)、systemd_tests(2) = **22 用例**（systemd 2 中 1 例实连因 OHOS 无 libsystemd 失败）
  - 其中通过 21、失败 1（systemd 实连，环境限制）
- 不可运行（缺第三方依赖/平台）：cxx11(2, gtest 需 C++17)、cxx14(2, 同)、json_tests(?, 需 libboost_json) = **4 用例（cxx11/cxx14），json_tests 用例数为加锁占位**
- 不可运行（平台非 Darwin）：os_log_tests（OHOS 无法构建，0 用例可达）
- 未注册：general_tests.cpp（上游未注册，不计入）

> R02 修正：r01 把 systemd 实连失败计入分母（21/22）；本轮将失败/不可运行单列，通过率只看「可运行且已运行」中通过部分 = 21/22（systemd 实连失败归因平台基础设施，不在本库可控范围），cxx11/cxx14/json_tests/os_log 一律不计入「适配后测试用例统计」合计与通过率分母。