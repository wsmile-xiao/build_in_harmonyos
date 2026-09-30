# ympd 1.3.0 HarmonyOS PC 适配笔记

## 任务与源码

- 软件：ympd 1.3.0，MPD 的轻量级 Web 控制界面
- 上游仓库及标签：https://github.com/notandy/ympd/tree/v1.3.0
- 源码归档：`https://github.com/notandy/ympd/archive/refs/tags/v1.3.0.tar.gz`
- SHA-256：`D9F68920CD93D1CFA971E1D7B9162A2B1724909BC9753C1338CECB3688D234D5`
- 源码由官方标签归档下载并核验散列值；目标设备无法连接 GitHub，真机构建使用这份同散列官方归档的本地副本。

## 上游测试清点（R51）

- 官方 v1.3.0 源码树没有 `tests/`、`test/` 或 `test_package/` 目录，也没有独立测试源文件。
- `CMakeLists.txt` 与 `cmake/` 下没有 `enable_testing()`、`include(CTest)` 或 `add_test()` 注册。
- 在构建目录运行 `ctest -N` 得到 0 个注册测试。因此上游测试为 0 项，0/0 可运行；测试空缺由下方消费者和真机测试补充。

## HarmonyOS 构建环境

- 设备：HarmonyOS PC，AArch64
- 编译器：Clang 15.0.4
- CMake：4.1.2
- Conan：2.29.1
- 依赖：`libmpdclient/2.23`（HarmonyOS AArch64 shared 包）、`openssl/3.5.8.1`（HarmonyOS AArch64 static 包）

## 适配内容

1. 上游 `CMakeLists.txt` 将 v1.3.0 的运行时版本宏写成了 1.2.3。补丁修正为 1.3.0，消费者测试对此做精确断言。
2. `mpd_client.h` 在多个翻译单元中定义全局 `mpd` 对象。Clang 15 的默认 `-fno-common` 导致链接时报 duplicate symbol；补丁改成 `extern` 声明并在 `mpd_client.c` 中单一定义。
3. Conan CMakeDeps 生成导入目标；配方将目标和头文件路径映射到上游查找模块使用的 `LIBMPDCLIENT_*` 与 `OPENSSL_*` 变量。
4. CMake 4.1.2 不再接受低于 3.5 的最低版本声明。`CMake.configure()` 在命令行传入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`；该参数不能只放入工具链文件，因为上游的 `cmake_minimum_required()` 先于工具链加载。
5. `WITH_DYNAMIC_ASSETS=OFF` 保留上游默认的内嵌网页资源模式，避免运行时依赖源码目录。

## 构建与验证

- Conan 配方：`conanfile.py`，包类型为 application，安装 `bin/ympd` 和手册页。
- Conan 依赖检查：`libmpdclient/2.23`、`openssl/3.5.8.1` 的 HarmonyOS AArch64 包已从 `ohpcd` 下载并用于构建。
- Conan 构建及消费者测试：真机 `conan create` 构建、安装成功；`test_package` 5/5 断言通过（版本、服务启动、HTTP 状态和内嵌页面）。
- HarmonyOS 专项测试：`test_ohos/run_ohos_test.sh` 检查 ELF64/AArch64，并在设备上执行相同消费者测试；6/6 检查通过。
- 本地包级 CI：L0、L1、L4、L5 通过，构建成功率 100%。L2 冒烟跳过：CI 直接启动二进制且未加载 Conan runenv，设备系统路径中没有 `libmpdclient.so.2`；Conan 消费者及真机专项测试均在 runenv 下实际启动并通过。
- CI 快照未包含 `knowledge/graph/`，所以该快照的知识图谱门禁报告 `no_graph`；本地 `ohc-run.py graph validate` 已通过（541 个 `.kv`、541 个 Markdown 文件、541 条索引，169 条既有语料告警）。
- 仓库级 `tests/run_all.py` 为 10/12 套通过；另外 2 套在 `upstream/main` 基线上也因环境缺项失败：worker Git 可执行文件不可用，以及缺少 `knowledge/recipes/catalog.tsv`。
- 真机构建时因设备无法连接 GitHub，使用散列已核验的官方源码归档副本；临时验证配方仅替换源码读取方式，正式配方仍使用官方 URL 和相同 SHA-256。

## 最终状态

- 编译结束：2026-09-27；状态：built。
- 测试统计与环境说明见 `reports/test-report.md`。
