# cppdap 1.58.0a 适配笔记

## 官方来源核验

- 官方仓库：https://github.com/google/cppdap
- 标签：`dap-1.58.0-a`（GitHub API 唯一标签，commit 252b56807b532533ea7362a4d949758dcb481d2b）
- 版本映射：任务版本 `1.58.0a` 对应上游标签 `dap-1.58.0-a`（DAP 1.58.0 协议）
- tarball：https://github.com/google/cppdap/archive/refs/tags/dap-1.58.0-a.tar.gz
- SHA-256：5d35ca5db78570b6bef698e3365f79bd82a4f78e8393546387f78d7bdb2a2a08（本机下载实测）
- 许可证：Apache-2.0
- 上游 CMake 工程版本字段为 1.59.0（project(cppdap VERSION 1.59.0)），与标签版本不一致，配方版本以任务要求的 1.58.0a 为准

## 项目结构

- CMake 库项目（cmake_minimum_required 3.13，LANGUAGES CXX C，C++11）
- 库目标：`cppdap`（`add_library(cppdap STATIC ...)`，恒为静态库）
- 公共头：`include/dap/*.h`（session / protocol / io / typeinfo 等）
- 源码：`src/*.cpp`（content_stream / io / network / session / socket 等 + 按 JSON 后端选择的 serializer）
- 示例：`examples/hello_debugger.cpp`、`examples/simple_net_client_server.cpp`
- 测试：`src/*_test.cpp` 共 13 个文件，gtest 驱动，产物为单个 `cppdap-unittests` 二进制
- JSON 后端三选一：`CPPDAP_USE_EXTERNAL_NLOHMANN_JSON_PACKAGE` / `RAPIDJSON` / `JSONCPP`，否则走 `third_party/json` 子模块（发布包不含）

## 依赖

- 唯一运行时依赖：`nlohmann_json/3.12.0`（制品仓已发布 built 状态，header-only）
- 上游测试依赖：googletest 源码（发布包不含 `third_party/googletest` 子模块）
- 配方 vendor 的 googletest：`release-1.12.1`（https://github.com/google/googletest/archive/refs/tags/release-1.12.1.tar.gz，sha256 见 ohpcd archives/g/googletest/1.12.1/conandata.yml），仅用于上游测试构建，不进入最终产物
- 测试构建加 `-DCMAKE_CXX_STANDARD=14`，满足 googletest 1.12 的语言版本要求，库本身仍兼容 C++11

## 编译步骤

1. 主库：裸 cmake + 自发现 `ohos.toolchain.cmake`，`-DOHOS_ARCH=arm64-v8a`，`-DCPPDAP_USE_EXTERNAL_NLOHMANN_JSON_PACKAGE=ON`，测试/示例/fuzzer 全部 OFF，`cmake --build` 后 `cmake --install`
2. 上游测试：vendor googletest 源码至 `build/gtest-src`，另建 `build-upstream-tests` 目录，`-DCPPDAP_BUILD_TESTS=ON` + `-DCPPDAP_GOOGLETEST_DIR=<gtest-src>` + 同一套 OHOS 工具链与依赖预加载，构建 `cppdap-unittests` 并直接运行，解析 gtest 摘要后输出 `HMBS_UPSTREAM_TEST_RESULT`
3. test_package：标准 CMakeDeps + CMakeToolchain 消费者构建，`ctest` 后直跑 `test_cppdap`，解析 `N/M checks passed` 后输出 `HMBS_TEST_PACKAGE_RESULT`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 发布包缺 `third_party/json`，默认 JSON 探测直接 FATAL | GitHub archive 不含子模块 | 强制 `-DCPPDAP_USE_EXTERNAL_NLOHMANN_JSON_PACKAGE=ON` 并依赖制品仓 `nlohmann_json/3.12.0`，配合 `ohos-find-deps.cmake` 让 `find_package(nlohmann_json CONFIG)` 可达 |
| 2 | `CPPDAP_BUILD_TESTS=ON` 无 gtest 源码时仅警告后静默关闭 | 上游 CMake 缺子模块时 `set(CPPDAP_BUILD_TESTS OFF)` | 配方内 vendor googletest 1.12.1 源码并显式传 `CPPDAP_GOOGLETEST_DIR`，保证测试真构建真运行 |
| 3 | 上游 `CMAKE_SYSTEM_NAME` 分支仅处理 Windows/Linux/Darwin | OHOS/HarmonyOS 命中不到 `pthread` 分支 | `package_info()` 对 `Linux` 与 `OHOS` 均声明 `pthread` 系统库，Windows 声明 `ws2_32` |
| 4 | 上游库恒为 `STATIC`，`BUILD_SHARED_LIBS` 透传无效 | `add_library(cppdap STATIC ...)` 写死 | 保留 `shared` 开关仅作 Conan 惯例，行为以静态库为准并在文档中说明 |
| 5 | 真机 `CPPDAP_BUILD_TESTS=ON` 仍报 `third_party/googletest submodule missing`，`cppdap-unittests` 未生成；第二轮 `.patch` 文件报 `patch stream is incomplete` 解析失败 | 上游以 `CPPDAP_GOOGLETEST_DIR/.git` 判断 gtest 是否存在，vendor tarball 无 `.git` 被静默 `set(CPPDAP_BUILD_TESTS OFF)`；独立 patch 文件头行号与 conan 解析器不兼容 | 改用配方内 `replace_in_file` 在 `build()` 首步将门禁改写为 `googletest/src/gtest-all.cc` 源码存在性检查，不再使用独立 `.patch` 文件；vendor 改为校验该文件，二进制查找加递归兜底 |
| 6 | 真机 `test_cppdap` 在 `RUN: ... ./test_cppdap` 报 `Signal 9`，`conan create` 退出码 137 | `test_cppdap.cpp` 写 8 字节后 `read(buf, 31)`；上游 `src/io.cpp Pipe::read` 循环等待填满请求字节数才返回（不满则 `cv.wait`），测试永久阻塞后被看门狗 SIGKILL；前次 bash 包裹/绕开 ctest 未触及该逻辑 | 请求字节数改为恰好 `len`（`read(buf, len)`），语义与实现一致，不再超额等待 |
| 7 | 真机 `HMBS_TEST_PACKAGE_RESULT` 13/13 通过但判 `incomplete`（缺 `HMBS_UPSTREAM_TEST_RESULT`） | 上游标记只在主配方 `build()` 输出，而 HMBS 门禁只扫描 `test_package` 阶段 stdout；Conan 缓存命中时 `build()` 被跳过，标记自然缺失（c4log/dkjson/aiohttp 均已用 test_package 转发规避） | `build()` 将真实 gtest 汇总写入 `upstream_test_result.json` 并随包发布到 `res/`，`test_package/test()` 从 `package_folder/res` 原样转发标记（`print` + `output.info` 双通道），数字仍来自真实 `./cppdap-unittests` 运行 |

## 依赖版本

- nlohmann_json/3.12.0
- googletest release-1.12.1（仅上游测试构建期 vendor，不作为 Conan 依赖发布）

## 验证结果

- 本轮仅完成未提交工作树，尚未执行真机预检
- 待 HMBS 后台预检回填：`conan create` 主库构建、`cppdap-unittests` 全量运行、`test_cppdap` 消费者测试
- 证伪计划：确认 `cppdap-unittests` 输出非空且含 `[ RUN ]` 明细；必要时用失败桩验证 harness 可捕获失败；区分通过与静默跳过

## 交付物

| 文件 | 说明 |
|------|------|
| archives/c/cppdap/manifest.yaml | 软件级 manifest |
| archives/c/cppdap/README.md | 软件级说明 |
| archives/c/cppdap/1.58.0a/conanfile.py | 主配方 |
| archives/c/cppdap/1.58.0a/conandata.yml | 源码 URL + sha256 |
| archives/c/cppdap/1.58.0a/manifest.yaml | 版本级 manifest |
| archives/c/cppdap/1.58.0a/test_package/ | 消费者测试与 MANIFEST.yml |
| archives/c/cppdap/1.58.0a/notes.md | 本文件 |

## 注意事项

- `conanfile.py` 的 `url` 指向官方仓库，避免模板占位写法
- 未引入任何补丁，`patches: {}` 保持空映射
- 上游测试二进制为单体 `cppdap-unittests`，MANIFEST.yml 按 13 个源文件逐项列出测试来源
