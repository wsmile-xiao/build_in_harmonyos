# sheenbidi 3.0.0 — HarmonyOS PC 适配说明

## 概况

SheenBidi 是 Unicode 双向算法（UBA）的轻量实现：为双向文本的段落/行解析嵌入层级并
计算视觉 run，另含镜像定位（SBMirrorLocator）与脚本定位（SBScriptLocator）。

- 上游：https://github.com/Tehreer/SheenBidi （源码取自 Debian orig tarball）
- 形态：C 共享库/静态库 + 头文件（`include/SheenBidi`）
- 依赖：仅标准 C 库（`stddef.h`/`stdint.h`/`stdlib.h`/`string.h`）
- 许可证：Apache-2.0

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 纯 C、无平台相关代码 | OHOS clang 直接构建，无需补丁（`patches: []`） |
| 2 | 测试仅在非 unity 模式构建 | `BUILD_TESTS = BUILD_TESTING && !SB_CONFIG_UNITY` → 配置 `-DSB_CONFIG_UNITY=OFF -DBUILD_TESTING=ON` |
| 3 | 测试 `main` 恒返回 0 | 失败由 CMake 的 `FAIL_REGULAR_EXPRESSION "[1-9][0-9]* error"` 判定 → 用 `ctest` 运行 |
| 4 | 测试数据 | 每个测试以 `Tools/Unicode` 目录为 `argv[1]`（随 tarball 提供） |
| 5 | 共享设备测试超时 | 默认每测例 60s 偏紧 → `ctest --timeout 600` |
| 6 | CMake 目标名 | 安装导出为 `SheenBidi::SheenBidi` → 包信息 `cmake_file_name=SheenBidi`、`cmake_target_name=SheenBidi::SheenBidi` |

## 测试

### 上游

自定义 `STANDALONE_TESTING` 套件，`CMakeLists.txt` 注册 **16** 个测试可执行文件：
`AlgorithmTests`（Unicode BidiTest/BidiCharacterTest 一致性 + 镜像 + 括号对）及
Allocator/Atomic/BidiTypeLookup/BracketLookup/BracketQueue/CodepointSequence/Codepoint/
GeneralCategoryLookup/MirrorLookup/Once/RunQueue/ScriptLocator/ScriptLookup/Script/
ThreadLocalStorage 共 15 个其余套件。取数：`ctest -N` → 16。

`build()` 在真机执行 `ctest --output-on-failure --timeout 600`，要求 16/16 通过
（失败由上游的 `FAIL_REGULAR_EXPRESSION` 捕获）。

### 消费者测试（test_package，CMake + ctest）

`test_package/test_sheenbidi.c` 共 **12** 条断言，基于上游/Debian 的 smoke test：

- 混合阿语/拉丁串 `"یہ ایک )car( ہے۔"`：段落长度、**3 个 level run** 的精确
  offset/length/level（16/8/1、13/3/2、0/13/1）、镜像定位恰好 2 个且
  `index16 (40→41)`、`index12 (41→40)`
- 纯 LTR `"hello"`：单 run、level 0
- 纯希伯来 `"שלום"`：单 run、level 1

## 已知限制

- 未启用实验性 Text API（`SB_CONFIG_EXPERIMENTAL_TEXT_API=OFF`，与上游默认一致）。
- 未做多线程压力测试（仅覆盖 ThreadLocalStorageTests）。
