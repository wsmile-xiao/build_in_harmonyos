# cpp-dump 0.7.0 适配笔记

## 编译环境
- 构建系统: cmake（上游仅 CMakeLists.txt，min 3.12）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / clang++（OHOS SDK libc++）
- 状态: built

## 编译步骤

1. 下载 tag 源码（conandata.yml，sha256 与 conan-center-index 同源一致）。
2. `apply_conandata_patches` 应用 5 个补丁（2 个测试夹具选择分支 + 3 个新增 ohos 夹具）。
3. 把源码树拷贝到 `<build_folder>/cpp-dump`（目录名必须恰为 `cpp-dump`，见问题 3）。
4. `cmake -S <build_folder>/cpp-dump -B <build_folder> -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake`
   （profile 注入 CMAKE_CXX_STANDARD=17 / build_type=Release），`cmake --build`。
5. `ctest --output-on-failure`：27 个上游用例在 build 阶段执行。
6. `cmake --install` 装 `cpp-dump.hpp` + `cpp-dump/`（35 个头）到 `include/`，LICENSE 到 `licenses/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备默认编译 std 低于 17，`-Werror` 报 `inline variables are a C++17 extension` 等 | 上游要求 C++17，裸 cmake 默认 std 不足 | profile `compiler.cppstd=17`（CMakeToolchain 注入 CMAKE_CXX_STANDARD=17）；原生探索亦显式 `-DCMAKE_CXX_STANDARD=17` |
| 2 | `dump-variable` / `color-variable-{original,by_syntax}` 3 个用例夹具不匹配 | HarmonyOS 用 libc++，unordered 容器迭代序与上游 linux（libstdc++）夹具不同；实测本平台输出与上游 apple（libc++）夹具**逐字一致**（diff 为空） | 补丁 0001/0002 在 os 分支最前加 `CMAKE_HOST_SYSTEM_NAME STREQUAL "HarmonyOS"` → 新增 ohos 夹具（补丁 0003/0004/0005，内容与 apple 夹具一致）；linux/apple/win32 分支原样保留 |
| 3 | `log-label-test` 不匹配：`[.. 0.work/test/log_label_test.cpp:146]` vs 期望 `[.. p-dump/test/...:146]` | 上游 `log_label::fixed_length(0,40,0)` 取 `__FILE__` 尾 34 字符，期望源码目录名恰为 `cpp-dump`（GitHub Actions 检出目录）；conan 缓存源码目录名不满足 | conanfile `build()` 先把源码 `copytree` 到 `<build_folder>/cpp-dump` 再 configure（不改上游测试）；原生验证用同名软链同理 |
| 4 | `init-build` 把纯 CMake 工程判成 `BUILD_SYSTEM=autotools`，`conan-init` 随之生成 autotools 模板（占位 sha256 + 空壳 test.c） | 已知缺陷（feedback 2026-09-26 ctml/ctml 同型第 2 例）：构建系统按 URL 关键词猜 | 手工改 `.build-context` 的 BUILD_SYSTEM=cmake 并重写全套配方文件 |

## 源码修改（5 个补丁，全部 test/ 面）

- `0001-test-color_variable_test.cmake.patch` / `0002-test-dump_variable_test.cmake.patch`：os 夹具选择分支最前增加 HarmonyOS 分支（仅选择新夹具，不改任何断言）。
- `0003/0004/0005-test-txt-*.patch`：新增 `color_variable_ohos_{original,by_syntax}.txt`、`dump_variable_ohos.txt` 三个夹具（内容与上游 apple 夹具逐字一致）。
- 库源码（`cpp-dump.hpp`、`cpp-dump/**`）零改动。

## 依赖版本

- conan 依赖：0（header-only，仅标准库 + `<cxxabi.h>` 编译器运行时）
- 构建工具：cmake、clang 15（均由设备/CI 环境提供）

## 验证结果

```bash
# 原生（沙箱 HOME，源码目录名 cpp-dump）
cmake -S <cpp-dump> -B <build> -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_EXTENSIONS=OFF
cmake --build <build> -j4      # BUILD_RC=0
ctest --output-on-failure      # 100% tests passed, 0 tests failed out of 27（Total Tests: 27）
# conan 采信轮（清缓存干净轮）：见 $TASK_DIR/evidence-index.json 与 reports/
```

## 注意事项

- 上游测试在 `build()` 内执行（CI L1c 门禁要求 build 阶段日志含 ctest）。
- 上游当前 HEAD 注册 29 个用例（readme 净 +2，+4/−2 逐项归因见 `test_package/MANIFEST.yml`）；被审 tag v0.7.0 注册 27 个，全量实跑。
