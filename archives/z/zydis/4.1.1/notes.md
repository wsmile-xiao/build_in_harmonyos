# zydis 4.1.1 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++
- 状态: built（待真机预检）

## 编译步骤

CMake 流程，依赖 Conan 已发布的 `zycore-c/1.5.2`（上游 4.1.1 对应 Zycore 1.5.x，xmake 映射为 v1.5.2）：

```cmake
ZYDIS_BUILD_SHARED_LIB=False  # 默认静态
ZYDIS_BUILD_EXAMPLES=False
ZYDIS_BUILD_TOOLS=True        # 上游测试需要 ZydisInfo 等工具
ZYDIS_BUILD_TESTS=True        # 接入上游回归测试
ZYDIS_BUILD_DOXYGEN=False
ZYDIS_BUILD_MAN=False
ZYAN_SYSTEM_ZYCORE=True       # 使用 Conan 提供的系统 Zycore，不用 submodule
```

`build()` 按顺序执行 `cmake.configure()`、`cmake.build()`、`cmake.test()`（ctest）。

## 上游测试审计

- 来源：`tests/` 目录，`CMakeLists.txt` 中 `ZYDIS_BUILD_TESTS` 分支注册 2 个 ctest：
  - `ZydisRegression`：`tests/regression.py test <ZydisInfo>`，遍历 `tests/cases/*.in/*.out` 回归用例；
  - `ZydisRegressionEncoder`：`tests/regression_encoder.py`，使用 `tests/enc_test_cases.json` / `tests/re_enc_test_cases.json` 及编码 fuzz 工具。
- 测试仅需 Python3（真机已提供），无网络下载、无 GTest 依赖，可在真机完整执行。
- 实测通过数待真机预检回填，以预检日志 `ctest` 输出为准。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游默认用 `dependencies/zycore` submodule | 源码包不带 submodule，真机无网络拉取 | `ZYAN_SYSTEM_ZYCORE=True` + `requires zycore-c/1.5.2`，走 Conan 依赖 |
| 2 | 产物同时含库与命令行工具 | `ZYDIS_BUILD_TOOLS=True` 会安装 `ZydisInfo` / `ZydisDisasm` 到 bin | 按 R38 在软件级目录提供 `commands.json`（type tool），`package_info` 声明 `bindirs` |
| 3 | `Unknown CMake command "zyan_set_common_flags"`（`ZYAN_SYSTEM_ZYCORE=True` 时） | CMakeDeps 生成的 Zycore 查找模块只声明 `Zycore::Zycore`，不带 `zyan-functions.cmake`；该函数只在 `add_subdirectory(zycore)` 路径下可用 | `source()` 在 `locate_zycore()` 后注入带 `if(NOT COMMAND ...)` 守卫的兼容 fallback（`zyan_set_common_flags` 置 C_STANDARD 11，`zyan_maybe_enable_wpo` / `zyan_set_source_group` 置空），与上游 `zycore-c/1.5.2` 的 `zyan-functions.cmake` 语义一致 |
| 4 | `cache_variables` 的 `CMAKE_C/CXX_COMPILER` pin 未覆盖 profile 旧值（`project()` 第 8 行仍用缺失的 `/data/service/hnp/bin/clang`） | 生成的 `conan_toolchain.cmake` 中 profile 派生的编译器设置优先于用户 cache 变量，真机 profile 指向已迁移的旧路径 | `generate()` 后对已生成的单个 `conan_toolchain.cmake` 做精确替换（仅旧路径缺失且新路径存在时）并输出替换前后 `CMAKE_C/CXX_COMPILER` 行，另以 build scope 导出 `CC/CXX`（`hmbs_compiler.sh`）；CI 等旧路径有效时零改动 |
| 5 | 构建期 `fatal error: 'Zycore/Defines.h' file not found`（configure 已过，`cmake.build` 失败） | 上游以裸 target 名 `"Zycore"` 链接（仅 `add_subdirectory(zycore)` 路径存在）；CMakeDeps 只提供 `Zycore::Zycore`，裸名静默退化为 `-lZycore`，头文件目录不传播 | `source()` 将唯一一处 `target_link_libraries("Zydis" PUBLIC "Zycore")` 改为链接 `Zycore::Zycore`，与 CMakeDeps 日志建议的目标名一致 |
| 6 | `test_package` 构建期同样 `fatal error: 'Zycore/Defines.h' file not found`（主库已能编过） | 主库 `package_info()` 未声明对 `zycore-c` 的透传依赖，CMakeDeps 生成的 `zydis-config` 不做 `find_dependency(zycore)`，消费者只拿 `Zydis` 头目录而缺 `Zycore` 头目录（与 #5 同症状不同层面：#5 是主构建内 target 名，#6 是 Conan 包级依赖图） | `package_info()` 新增 `self.cpp_info.requires = ["zycore-c::zycore-c"]`，使 `Zydis::Zydis` 自动透传 `Zycore` 头目录/库；`test_package` 无需改动 |
| 7 | 上轮仅加 `package_info.requires` 后真机仍报同一缺头错误（构建哈希已变证明新配方已参检，`test_package` 仍停在 50%） | 仅靠透传 `INTERFACE_LINK_LIBRARIES` 未在消费者编译行物化 `Zycore` 头目录（`test_package` 仅 `find_package(zydis)`，`zycore` 配置未被显式消费） | 不同路线：`test_package/CMakeLists.txt` 显式 `find_package(zycore CONFIG REQUIRED)` 并链接 `Zycore::Zycore`（`zycore` 配置由传递依赖图自动生成，无需版本硬编码）；主包 `requires` 保留 |
| 8 | 上轮 `test_package/CMakeLists` 显式链接后预检日志仍显示旧提示（`find_package(zydis)` 单行、构建哈希 `zydis68e2b9afedd57` 未变），证明该轮测的是同步前旧树 | 消费者对 `zycore` 仅传递依赖，CMakeDeps 只按直接依赖生成提示，`zycore-config` 未被保证为直接依赖 | 不同路线：`test_package/conanfile.py` 的 `requirements()` 在 `tested_reference_str` 之外直引 `zycore-c/1.5.2`（与主配方同 pin），使 `zycore-config` 成为直接依赖并生成；CMakeLists 显式链接保留 |

## 源码修改

无补丁。Zydis 自称无第三方依赖（甚至无 libc 依赖），纯 C11，OHOS 兼容性好。

## 依赖版本

- `zycore-c/1.5.2`（制品仓已发布，见 `archives/z/zycore-c/1.5.2`）

## 验证结果

```bash
# 待 HMBS 真机预检（conan create，含 ctest + test_package）
```

- 本地 Windows 环境不运行 conan/真机构建；以上结论来自上游源码与 CMake 审计。
- 防证伪提醒：预检通过后需确认 ctest 实际执行用例数非零、参照文件非空，避免“静默通过”。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | CMake 配方（库 + 工具） |
| `conandata.yml` | 官方 GitHub 归档 URL + sha256 |
| `test_package/` | 解码/编码消费者测试 + ZydisInfo CLI 调用 |
| `commands.json`（软件级） | 声明 `ZydisInfo` / `ZydisDisasm` 工具 |
