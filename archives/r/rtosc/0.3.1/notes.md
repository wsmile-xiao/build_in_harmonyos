# rtosc 0.3.1 适配笔记

## 编译环境

- 构建系统：cmake
- 上游：https://github.com/fundamental/rtosc（tag v0.3.1，commit f3882fedab283e028514d40415ab64ea48d4b3a1）
- 源码包：https://github.com/fundamental/rtosc/archive/refs/tags/v0.3.1.tar.gz
- 源码 SHA256：41989b5811ae5a05667b3743b1fc8309010609a68e78a5eebb2a85cfe2aa1743（已用 Python urllib 下载 182549 字节实测）
- 许可证：MIT
- 编译器：clang/clang++（Conan `tools.build:compiler_executables` 解析，HMBS 真机注入优先）
- 状态：built（首轮仅完成工作树，待 HMBS 真机预检回填实测数字）

## 编译步骤

1. `get()` 下载官方 tag 归档并校验 SHA256。
2. `generate()` 经 CMakeToolchain 配置：
   - OHOS 下固定 `CMAKE_SYSTEM_NAME=Linux`（上游安装规则与 `GNUInstallDirs` 仅识别 Linux；rttr/zstr 同款做法），`CMAKE_SYSTEM_PROCESSOR=aarch64`；
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容上游 `cmake_minimum_required(VERSION 2.8)`；
   - `BUILD_SHARED_LIBS` 与 `RTOSC_BUILD_SHARED_LIBS` 跟随 Conan `shared` 选项（默认 OFF）；
   - `BUILD_RTOSC_EXAMPLES=OFF`、`PERF_TEST=OFF`（示例需 JACK/GUI，perf/serializer 为 opt-in）。
3. `cmake.configure()` + `cmake.build()` 产出 `rtosc`（C）与 `rtosc-cpp`（C++）。
4. `build()` 内运行 `_run_upstream_ctest`：先 `ctest -N` 取分母（`Total Tests: 28`），再 `ctest --output-on-failure` 全量执行并逐行解析 `Test #N` 状态；双通道输出 `HMBS_UPSTREAM_TEST_RESULT` 并持久化 `hmbs_upstream.json`；分母漂移、空日志、无 `Test #` 行、恒等式不成立均直接失败。
5. `package()` 经 `cmake.install()` 安装库、头文件与 pkg-config，再将 `hmbs_upstream.json` 复制到 `res/` 供 test_package 原样重放。
6. `test_package` 构建 `test_rtosc.cpp`（11 项真实 API 断言）并运行，输出 `HMBS_TEST_PACKAGE_RESULT` 后重放包内上游证据。

## 上游测试审计

- 审计对象：v0.3.1 tag 源码包内 `CMakeLists.txt`（注意 master 分支已演进为 31 项，不可混用）。
- 默认配置（OHOS，无 liblo/JACK/Ruby，`PERF_TEST` OFF）注册 28 项，口径 `ctest_entries`：
  - C（15）：version、util、osc-spec、arg-val-cmp、arg-val-math、pretty-format、simple-messages、null-messages、bundles、patterns、nested-bundles、fat-message、empty-strings、message-alignment、test-arg-iter。
  - C++（13）：test-midi-mapper、metadata、apropos、default-value、headerlib、test-walker、walk-ports、path-search、undo-test、sugar、typed-template-test、path-collapse、test-automation。
- 条件项（OHOS 下不存在，不计入分母）：`liblo`（需 `pkg_check_modules(LIBLO liblo>=0.28)`）、`performance`/`serializer`（需 `PERF_TEST=ON`）、`port-checker*`（需 `LIBLO_FOUND AND RUBY_FOUND`）。
- 取数命令（v0.3.1 源码包内）：`ctest -N` 显示 `Total Tests: 28`；配方内以此为分母硬断言，漂移即失败。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `cmake_minimum_required(VERSION 2.8)` 在 CMake 4 下被拒绝 | 老版本下限低于 CMake 4 支持的 3.5 | 配方传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，不改上游源码（rttr 同款） |
| 2 | 上游安装规则在 HarmonyOS 下不执行 | `install()` 与 `include(GNUInstallDirs)` 均以 `CMAKE_SYSTEM_NAME MATCHES "Linux"` 为守卫 | OHOS 下固定 `CMAKE_SYSTEM_NAME=Linux`（rttr/zstr 同款），复用官方安装路径 |
| 3 | master 与 v0.3.1 测试数不一致 | master 新增 `rtosc-time` 等用例并重组 C/C++ 划分 | 严格按 v0.3.1 tag 审计为 28 项，MANIFEST 与配方常量均以此为准 |
| 4 | Windows 工作站无法完整检出上游 main | `archives/g/gama` 下文件名含 `??`，Windows 非法；`archives/l/libXext` 与 `libxext` 大小写碰撞 | 稀疏检出排除 `archives/g/gama/`；`libxext` 碰撞为环境限制，保持未提交，不纳入本 PR |

## 源码修改

无补丁。`patches/` 目录未创建，`conandata.yml` 无 `patches` 段。

## 依赖版本

无编译依赖。`requirements()` 为空；工具链仅需 CMake 与 C/C++ 编译器（HMBS 真机注入）。

## 验证结果

```bash
# 首轮仅完成工作树，以下待 HMBS 真机预检回填：
#   conan create archives/r/rtosc/0.3.1 -pr:h=ci/conan/profiles/ohos-aarch64 ...
# 预期：ctest 28/28，test_rtosc 11/11，日志含 HMBS_UPSTREAM_TEST_RESULT 与 HMBS_TEST_PACKAGE_RESULT。
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | CMake 配方（含 28 项 ctest 全量证据链） |
| `conandata.yml` | 官方 tag URL + 实测 SHA256 |
| `test_package/test_rtosc.cpp` | 11 项消费者断言（C 消息/Bundle/版本/匹配 + C++ Ports 分发） |
| `test_package/MANIFEST.yml` | 28 项上游审计 + 消费者声明 |

## 注意事项

- 本机为 Windows，不运行 conan；一切编译与测试数字以 HMBS 真机预检日志为准，PR 正文通过率留待 evidence 轮填写。
- 若真机出现可选依赖被意外探测到（如自带 liblo 的 worker），分母断言会立即失败并给出 `ctest -N` 实测值，届时按实际注册数处理，绝不静默跳过。
