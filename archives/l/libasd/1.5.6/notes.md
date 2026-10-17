# libasd 1.5.6 适配记录

## W0/W0b/R47

- 任务语言为 C++，源码主体为 C++，语言预检通过。
- 官方 tarball SHA-256：`746713b4b2e3dfbde6267f53bf53b2c8a7ef2fa433f201a9324ff7d4d854b49a`。
- 上游 README 明确 C++ 组件是仅依赖标准库的 header-only 库；Python binding 另依赖 pybind11。

## 上游构建取证

- 官方 release tarball 含 `.gitmodules`，但不含 `extlib/pybind11`。
- 根 CMake 无条件 `add_subdirectory(extlib)`、`add_subdirectory(python)`；`extlib/CMakeLists.txt` 在目录缺失时尝试 `git submodule init/update`，随后仍无条件 `add_subdirectory(pybind11)`，因此干净 release 源码 configure 失败。
- 上游测试目录包含 6 个 Boost.Test C++ 源文件；测试配置依赖 Boost，但在缺少 pybind11 的更早阶段无法进入测试。
- 最小真实 consumer 以 OHOS clang++、C++11 包含 `<libasd/libasd.hpp>` 并通过 `to_voltage` API 编译。

## Conan 包与消费者验证

- recipe 按公开 C++ header-only 组件打包 `libasd/*.hpp`，不引入未锁定的 Python/pybind11 依赖。
- test_package 真实链接 `libasd::libasd`，执行两个 `to_voltage` API 检查。

## 路径 B 判断

- 本任务走路径 A+B：A 交付可消费的 C++ header-only 包；B 固化“release tarball 缺少子模块且顶层 CMake 强制进入可选绑定路径时，应分离核心组件与绑定组件、保留 configure 原始证据”的可复用经验。
- Python binding 未适配、上游 Boost suite 未执行，均在 manifest/notes/report 单独申报；不将 C++ consumer 结果冒充 Python 或 Boost 测试通过。

## 发现与知识

- ✅ release tarball 的 `.gitmodules` 不等于子模块源码已随包发布；libasd 的顶层 CMake 会强制进入缺失的 pybind11 绑定路径，核心 C++ header 可独立分离打包。
- ✅ 该经验已关联草稿：`knowledge/drafts/DRAFT-libasd-forced-optional-python-submodule.kv`。

## 对话记录

### 对话 #1（2026-09-03）

- 先复核 release 内容和 `.gitmodules`，确认不是语言不匹配；最小 C++11 根头 consumer 通过后再建立 header-only recipe。
- 不下载未锁定 pybind11，不把 Python 绑定依赖或 submodule 源码捎带进本软件 PR。

## 上游 Boost.Test 实跑（2026-09-05 更新）

- 阻塞解除：0001 补丁将 `add_subdirectory(extlib)`/`add_subdirectory(python)` 移入默认关闭的 `LIBASD_ENABLE_PYTHON_BINDING`，并修正 `option(LIBASD_BUILD_TESTS ON)` 缺 description 导致测试默认关闭的上游 bug。
- 测试依赖：boost/1.84.0（ohpcd 制品仓已发布，`conan install --build=never` 核实）。6 个测试均为 header-only `<boost/test/included/unit_test.hpp>`。
- 实跑命令（设备原生）：
  `cmake -S . -B build-test -DBOOST_ROOT=<boost包> -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_POLICY_DEFAULT_CMP0167=OLD -DLIBASD_BUILD_TESTS=ON -DCMAKE_CXX_FLAGS=-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE -DCMAKE_BUILD_TYPE=Release`
  `cmake --build build-test -j1 && ctest --output-on-failure`
- 结果：**6/6 通过，0 失败，0 跳过**（Total Test time 0.82s），日志：`reports/upstream-boost-test-ctest.log`。
- 上游测试修改说明（2 处，均为可移植性修正，不改变断言语义）：
  1. `test/test_read_binary_as.cpp`、`test/test_write_as_binary.cpp`：`std::uniform_int_distribution<T>` 对 `char` 在 libc++（OHOS SDK）按 [rand.req.dist] 静态断言失败；改为小整型用 `int` 分布并回转 `T`，值域与语义不变。
- 测试构建额外说明：`BOOST_SP_NO_PTHREAD_SETCANCELSTATE`（OHOS pthread.h 不声明该函数，Boost 自带守卫）；CMake 4.x 需 `CMP0167=OLD` 以启用 FindBoost 模块模式（制品仓 boost 包无 CMake config）。
- Python binding 仍未构建：pybind11 未在 ohpcd 制品仓发布（2.10.1/2.10.3/2.11.0/2.12.0/2.13.6/2.14 实测缺失），其适配任务 #5963 因 R47 语言预检 env_unsupported（detected=python），绑定依赖缺失属外部生态阻塞，已在 PR 正文申报。

## 结束

最终状态: built（C++ header-only 组件；Python binding/上游 Boost suite 未声称完成）
---

**编译结束**: 2026-09-05 00:40
**最终状态**: built
