# Morpheus 2.4.1 CLI 适配记录

## 状态

- 构建系统: cmake
- 评估日期: 2026-07-28
- 当前范围: CLI simulator only (`MORPHEUS_GUI=OFF`)
- 当前状态: OHOS 真机 `conan create + test_package` 通过
- 本地限制: Windows 本机不作为最终验证环境；最终结果以 OHOS 真机 wrapper r15 为准

## 执行计划

1. 先补前置依赖，避免 Morpheus 构建阶段联网或缺库。
2. 按路径 A 的 CLI-only 适配推进，不进入路径 B。
3. 在 OHOS 真机上按依赖链执行 `conan create`。
4. 用 `test_package` 跑最小 MorpheusML smoke，确认包内 `bin/morpheus` 可真实执行。

## 已确认事实

Homebrew 当前 Morpheus 版本为 `2.4.1`，源码 URL 和 SHA256 已写入 `conandata.yml`。Homebrew 配方已在 2026-05-19 因 Qt5 EOL 标记 deprecated；这影响完整 GUI 适配判断，但不是 CLI-only 适配失败证据。

上游源码中存在两个主要产物：

| 产物 | CMake target | 输出名 | 当前处理 |
|------|--------------|--------|----------|
| CLI simulator | `MorpheusSIM` | `morpheus` | 本次适配目标 |
| GUI | `MorpheusGUI` | `morpheus-gui` | 本次关闭 |

CLI 核心依赖来自源码 `morpheus/CMakeLists.txt`：

- `Boost COMPONENTS program_options filesystem`
- `xtl`、`xsimd`、`xtensor`
- `ZLIB`
- `TIFF`
- 构建期 `xsltproc`

## 已完成的前置依赖

- `xtl/0.7.7`: PR !3287 已合入并发布。
- `xsimd/13.2.0`: PR !3359 已合入并发布。
- `xtensor/0.25.0`: PR !3360 已通过 CI/讨论门禁，等待审批/测试人门禁。
- `boost/1.90.0.1`: PR !3409 已通过 CI/讨论门禁，Morpheus 适配使用的本地缓存 revision 已额外补齐所需模块。
- `libxslt/1.1.45.1`: PR !3368 已合入并发布。
- `libtiff/4.7.2`: PR !2253 已合入；Morpheus 真机 r15 已从本地 Conan 缓存成功解析并消费。

## Morpheus recipe 要点

- `package_type = "application"`，软件级目录已添加 `commands.json`。
- host 依赖：`boost/1.90.0.1`、`xtl/0.7.7`、`xsimd/13.2.0`、`xtensor/0.25.0`、`zlib/1.3.1.1`、`libtiff/4.7.2`。
- `libtiff/4.7.2` 的 CMake package 会通过 `find_dependency()` 继续查找它的 public CMake deps；recipe 因此显式声明 `libjpeg-turbo/3.2.0`、`zstd/1.5.7`、`libwebp/1.6.0`、`xz/5.6.2`，让 Morpheus 的 `CMakeDeps` 生成同目录 `*Config.cmake` 文件。
- build 依赖：`libxslt/1.1.45.1`，用于提供 `xsltproc`。
- CMake 配置明确关闭：
  - `MORPHEUS_GUI=OFF`
  - `MORPHEUS_STATIC_BUILD=OFF`
  - `MORPHEUS_GRAPHVIZ=None`
  - `MORPHEUS_OPENMP=OFF`
  - `BUILD_TESTING=OFF`
- 补丁 `0001-cmake-ohos-cli-conan-deps.patch`：
  - 将 OHOS/HarmonyOS 显式作为 UNIX-like 平台处理。
  - 在 OHOS 上避免 Release IPO/LTO 自动开启。
  - ZLIB/TIFF 优先链接 Conan CMake targets：`ZLIB::ZLIB`、`TIFF::tiff`。
- recipe 运行时源码修正：
  - 将 `uint` typedef 从 Windows/macOS 局部条件改成通用 guarded fallback，并在 OHOS 下对核心 targets 强制预包含生成的 `config.h`。
  - 在 `MORPHEUS_OPENMP=OFF` 时为上游 OpenMP guard 提供 `std::mutex` fallback，避免未启用 OpenMP 时仍硬依赖 `omp.h`/`omp_lock_t`。
  - OHOS 下执行 CMake build/install 和签名工具命令时，将 SDK `llvm/lib` 前置到 `LD_LIBRARY_PATH`，避免 Conan 目标依赖中的 `libxml2.so.16` 抢先污染 `/data/service/hnp/.../llvm/bin/lld` 的运行时解析。
  - OHOS 下安装后对包内 `bin/morpheus` 做 ELF 签名。

## 验证设计

`test_package` 运行打包后的 `morpheus`：

```bash
morpheus --file smoke.xml
```

断言输出包含：

```text
Simulation finished
```

`smoke.xml` 是基于上游零步示例裁剪的最小 CLI 仿真模型，不包含 GUI、Graphviz、Gnuplot 输出或外部文件输入。

## 本地已做校验

- `python -m py_compile archives/m/morpheus/2.4.1/conanfile.py archives/m/morpheus/2.4.1/test_package/conanfile.py` 已通过。
- `git diff --check -- archives/m/morpheus` 已通过。

## OHOS 真机验证

- run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-morpheus-morpheus-2.4.1-pr3459-ci-fix-r3-sign-helper-20260801-233018-62929`
- result: `conan create` rc=0，Build Summary `Total: 1 / Success: 1 / Failed: 0`
- recipe revision: `morpheus/2.4.1#409f71df22b400f259f1aacb8ee1aa4a`
- package id: `f6b83d4cfd433fad8d9f95022f97c67e13d5c57a`
- package revision: `90bd5c197aa887f76a3e50f65c306722`
- full package ref: `morpheus/2.4.1#409f71df22b400f259f1aacb8ee1aa4a:f6b83d4cfd433fad8d9f95022f97c67e13d5c57a#90bd5c197aa887f76a3e50f65c306722`
- L0: pass，all checks passed
- L1: pass，test_package executed，smoke 输出包含 `Simulation finished`
- L1e: pass，反向删除 `bin/morpheus` 后 test_package 失败，证明 smoke 真实依赖包内二进制
- L2: skip，generic `--help/--version` 不适配 Morpheus CLI 输出口径；功能 smoke 已覆盖
- L4: pass，patches clean
- L5: pass，`bin/` 有内容

## 上游测试口径

- release 源码中识别到 10 个 GTest 可执行入口：`testCellSorting`、`runMotilityTests`、`runBaseTests`、`testCSMplane`、`runExpressionTests`、`runSystemTests`、`runFieldTests`、`runInitTests`、`runMembraneTests`、`runModelTests`。
- 2026-08-02 已在 OHOS 真机执行上游 GTest suite：构建/签名 run_dir `/storage/Users/currentUser/ohos-test-runs/codex-a-morpheus-upstream-gtest-r4-20260802-151701-21745`；有效 CTest run_dir `/storage/Users/currentUser/ohos-test-runs/codex-a-morpheus-upstream-gtest-r5-ctest-subdir-20260802-154259-31246`。
- GTest/CTest 实际注册 57 个 entry，`57/57` passed，`0` failed，`ctest_rc=0`，总耗时 `107.71 sec`；JUnit testcase count 为 57。详见 `upstream-gtest-20260802.md`。
- 计数口径：源码中粗略 grep 可见 59 个 `TEST(...)` 宏，但其中 1 个 `VDOUBLE.IDX_OPERATOR` 被 `#ifdef HAVE_VEC_INDEX_OPRT` 门控未编译，另 1 个旧 `System.Solver_RK4` 位于块注释内；因此本次可执行并注册的真实上游 GTest 数为 57。
- 测试 harness 只做环境适配：job-local 构建 GTest `v1.15.2`、跳过 upstream `3rdparty/GTest` 网络 clone、提供 `xxd -i input output` 兼容 wrapper、加载 Conan build/run env、CTest 前签名 build-tree ELF。上游测试断言未改。
- release 源码有 43 个 `Examples/**/*.xml` 官方模型示例；这些示例不是 upstream CTest，且多数依赖可视化/输出链：36 个包含 `Gnuplotter`、8 个包含 `TiffPlotter`、39 个包含 `ModelGraph`、28 个包含 `Logger`、4 个包含 `HistogramLogger`。当前 OHOS 包为 CLI-only，设备无 `gnuplot`，recipe 也设置 `MORPHEUS_GRAPHVIZ=None`；Examples 需按单独 runner 区分仿真核心、TIFF 输出、绘图/模型图输出能力，不能并入本次 GTest `57/57` 结果。

## 可能风险，不是已证实阻塞

- 远端 CI 需要 `boost/1.90.0.1` PR !3409 的补齐模块版本可被 Morpheus 解析；本地真机 r15 已用缓存验证可行。
- 完整 GUI 适配风险高，因为涉及 Qt5 EOL、Qt 插件、WebEngine/WebKit 和图形资源链；本 PR 明确只适配 CLI simulator。

## CI 跟进记录

- PR !3459 build #11923 已确认 `libtiff/4.7.2` 不再是缺失依赖：L0i 显示 registry 命中，Conan 图中 `libtiff/4.7.2#f386d7b671befab127228dbcfc6fe1bf` 从 ohpcd 下载并安装。
- 失败点位于 Morpheus configure：`build/Release/generators/TIFFConfig.cmake` 里的 `find_dependency(libjpeg-turbo)` 找不到同目录的 `libjpeg-turboConfig.cmake`。这是 Morpheus 只声明 `libtiff` 直接依赖时，`CMakeDeps` 未为 libtiff 的传递 CMake 依赖生成 config 文件造成的。
- 当前修复将 libtiff public CMake deps 显式列为 Morpheus 直接 requirements，并固定对应 `CMakeDeps` 名称，确保 `TIFFConfig.cmake` 的传递 `find_dependency()` 可以解析。
- 新端口隔离 job `morpheus-2.4.1-pr3459-ci-fix-r1` 中，`conan install --build=never` 已确认 `TIFF-release-armv8-data.cmake` 的依赖列表为 `ZLIB libjpeg-turbo zstd WebP xz`，生成目录存在对应 `ZLIBConfig.cmake`、`libjpeg-turbo-config.cmake`、`zstd-config.cmake`、`WebPConfig.cmake`、`xz-config.cmake`，缺失列表为空。
- 同一 job 的完整 `ci/conan/build_and_test.sh archives/m/morpheus/2.4.1` 通过，CMake configure 阶段声明 `TIFF::tiff` 后继续声明 `libjpeg-turbo::libjpeg-turbo`、`zstd::libzstd`、`WebP::webp`、`xz::xz`，未再出现 `Could not find libjpeg-turbo`。
- PR !3459 build #12149 进一步失败在最终链接 `MorpheusSIM`：`clang++` 启动 OHOS SDK `llvm/bin/lld` 时，动态加载到了 Conan 目标依赖路径中的 `libxml2.so.16`，导致 `xmlFreeDoc`、`xmlReadMemory` 等符号缺失。当前修复只调整 OHOS 工具链命令的 `LD_LIBRARY_PATH` 顺序，把 SDK `llvm/lib` 放在最前，保留后续 Conan 依赖路径，让 `lld` 加载匹配的 SDK runtime。
- 新端口隔离 job `morpheus-2.4.1-pr3459-ci-fix-r3-sign-helper` 完整重跑 PASS：链接阶段 `[100%] Built target MorpheusSIM`，未再出现 `libxml2`/`lld` 符号错误；package/sign/test_package 均完成，L0/L1/L1e/L4/L5 pass，L2 仍为既有 generic help/version skip。

## Path B 进入条件

当前不进入 Path B。只有满足以下条件之一，才写 Path B 报告：

- OHOS CI 对前置依赖或 Morpheus 本体给出可复现失败日志。
- 失败点需要不合理的大规模上游改造，且不能通过已有知识库模式解决。
- CLI smoke test 在构建通过后因目标系统能力缺失而无法运行，并有明确错误输出。

进入 Path B 时必须附上具体失败命令、错误摘要、涉及文件/行和已尝试绕行方案。
