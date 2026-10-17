# DRAFT-332 — rule4 新口径下上游 GTest 套件在 conan create 内真实执行

**场景**：人工审核新口径（PR #9656 2026-09-13 实证）——上游有用例而 0 测，
"平台限制/缺依赖/无环境"等理由均不接受，必须真实执行上游测试。

**结果**：openrct2 0.5.3 上游 test/tests/ 全量真实执行，ctest 逐用例
**274/274 通过**（静态口径 222 个 TEST 宏，运行时 TEST_P 参数化展开 274
实例；0 失败 0 跳过 0 豁免），conan create 流程内可复现，pkgid 不变。

## 四大根因与修法（速查）

### 1. GTest 依赖接法：test_requires 是正解，tool_requires 有坑

| 接法 | GTestConfig.cmake | LIBS/INCLUDE_DIRS | 结论 |
|------|-------------------|------------------|------|
| `tool_requires("gtest/x", visible=True)` + `CMakeDeps.build_context_activated=["gtest"]` | 生成 | **全空**（build context 组件 cpp_info 渲染不完整，conan 2.29.1 实测） | ❌ 编译报 `gtest/gtest.h not found`、链接报 `undefined symbol: testing::internal::...` |
| `test_requires = "gtest/x"` | 生成 | **全有值** | ✅ 正解 |

test_requires（conan 2 为测试框架设计的语义）：不进包运行时依赖图（pkgid
不变——包内容与不开测试完全一致）+ CMakeDeps 按完整 cpp_info 渲染。

**匹配前提**：gtest 配方的 `cmake_file_name` 需与上游 `find_package(<名>)`
一致——仓内 gtest/1.17.0.1 的 cmake_file_name=GTest / 组件 target
GTest::gtest，与上游原生匹配，**上游测试文件零修改**。

### 2. 测试资产三件套（"网络夹具不可用"的真实解法）

上游 CMake 在 **install 期**（DESTDIR 语义）下载测试数据，conan 流程不可达。
改为配方下载（URL+sha256 抄上游源码树 assets.json，与上游 CI 同源同版本，
`download(sha256=)` 强校验）：

| 资产 | 放置位置 | 缺失症状 |
|------|---------|---------|
| replays.zip（TEST_P 参数化输入） | source() 期 → 源码树 `test/tests/testdata/replays/`（上游 `file(CREATE_LINK testdata)` 符号链接自动带入 build；HMDFS 支持符号链接） | 用例数为 0（目录扫描空） |
| objects.zip（sv6/park 物件） | build() 期 → `$BUILD/data/object/` | `Unable to open park: missing objects` → `MapGetFootpathElement` 返回 null → **用例 segfault**（易误判为代码 bug，实为数据缺失） |
| openmusic.zip 的 object/ 部分（`openrct2.music.*`） | build() 期合并解压 | 特定 park（如 EverythingPark.park）加载失败 |

### 3. 运行时数据目录契约

测试二进制按 Platform.Linux `GetInstallPath` 搜索 `{exeDir,cwd}/data`——
组装 `$BUILD/data`（language ← 源码 data/language 符号链接 + object/ 解压
内容）即可命中，无需改上游代码。

### 4. 工具链告警豁免

上游全局 `-Werror`：gtest 1.17 头文件 EXPECT_LE/GE 模板在 clang15 下比较
size_t 与 int 触发 `-Wsign-compare`。顶层 CMakeLists 平台豁免段（上游
APPLE/riscv64 同款位置）加：

```cmake
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=sign-compare")
endif()
```

（-Werror 对其余告警依然生效；cache 里加 -Wno-error 会被上游 set 追加的
-Werror 覆盖——顺序问题，必须 patch 到 -Werror 之后。）

## ctest 执行环境（#9606 坑族）

```python
self.run(f'ctest --test-dir "{build}" --output-on-failure',
         env=["conanbuild", "conanrun"])
```

- conanbuild：工具链 llvm lib（libc++_shared.so）
- conanrun：依赖包 libdirs（libcurl/libpng/freetype/expat 等 .so）
- 单用任一都会缺库

## 用例数口径（审核对账）

- **静态口径**（grep TEST/TEST_F/TEST_P 宏）：222（与审核 N 一致）
- **运行时口径**（gtest_discover_tests 参数化展开）：274（ReplayTests 19 个
  parkrep 实例、StringTest TrimData 26 组、SimplePathfinding 9 参数等）
- 两者都对：正文统计表写"222（静态）/ 274（展开）"，验证结果按展开数报
  通过率（274/274 = 100%）

## 调试方法论（3 轮迭代实录）

1. 第 1 轮全量跑：TileElementsViewTests SetUpTestSuite 失败 → 缺
   `$BUILD/data`（language）——补数据目录
2. 第 2 轮：MapEdge 用例 segfault → sv6 加载 "missing objects"（objects.zip
   未就位）——放 2086 个 object 后恢复
3. 第 3 轮：RideRatings.EverythingPark 失败（RideGetCount 0 ≠ 529）→
   EverythingPark.park 引用 openrct2.music.*（在 openmusic.zip 不在
   objects.zip）——补 music 物件后恢复
4. 第 4 轮：274/274 全绿

每轮都以"逐用例真实报错原文"定位数据缺口，而非笼统豁免——新口径下这是
唯一合规的呈现方式。

## 与既有条目的关系（查重）

- DRAFT-matchit-r01-gtest-ohpcd-offline-run：手工 clang++ 直编上游测试源
  （配方外证据）——本条是**配方内 ctest 固化**（复现性更强），且补齐测试
  资产三件套与 tool_requires 渲染缺陷
- DRAFT-kangaru-4.3.2-catch2-submodule-test-requires：submodule 空目录场景
  的 test_requires——本条增量在 conan 2.29.1 tool_requires build context
  渲染缺陷的实证对比 + 资产机制 + ctest 环境

## 验证证据

- 本地 conan create：ctest `100% tests passed, 0 tests failed out of 274`，
  1757 行完整日志（reports/conan-create-tests4.log）
- pkgid `a53db40560517895afe33cb98682047db29f6519` 与不开测试完全一致
- CI #46137 PASSED（conan-build-test/test_package/L0/L1 全过）
