# jsonifier 0.9.97 上游测试全量枚举台账

任务要求：先完整枚举测试相关入口，再逐项分类和全量尝试运行；统计口径（全目录/用户测试源/实际运行）、全量通过率（通过数/发现总数）、未运行/不可运行/硬阻塞原因。

## 一、测试入口全量枚举（覆盖测试源、框架头、样例、基准、fixture、脚本、构建目标）

| 入口 | 类型 | 是否独立上游用例 | 分类理由 |
|---|---|---|---|
| Tests/main.cpp（921 行） | 基准程序主入口（Json-Performance） | 否 | 上游基准（benchmark）程序，非独立用例；且依赖 FetchContent 拉取 glaze/simdjson/BenchmarkSuite，CI 离线环境不可构建 |
| Tests/CMakeLists.txt | 构建目标 | 否 | 仅构建 Json-Performance 基准可执行文件（FetchContent 三个外部依赖） |
| Tests/Conformance.hpp + ConformanceTests/*.json（fail01-fail33 + pass1-3） | 用户测试源 | 是（31 项，fail01/fail18 标记 _EXCLUDE） | 独立 conformance 用例：解析非法/合法 JSON 并断言成功或失败 |
| Tests/Float.hpp + FloatValidation/test1-69.json | 用户测试源 | 是（69 项） | 独立浮点校验用例：每个 JSON 文件解析为 double 与 testValues 期望值比对 |
| Tests/Int.hpp + IntValidation/passTests.json、failTests.json | 用户测试源 | 是（59 项断言，2 个数据文件） | 独立整数校验用例：pass 数组逐项断言解析值，fail 数组逐项断言失败 |
| Tests/Uint.hpp + UintValidation/passTests.json、failTests.json | 用户测试源 | 是（43 项断言，2 个数据文件） | 独立无符号整数校验用例，同上 |
| Tests/String.hpp + StringValidation/test1-11.json（缺 4/7） | 用户测试源 | 是（9 项） | 独立字符串校验用例：解析 string 与 testValues 期望值比对 |
| Tests/RoundTrip.hpp + RoundTrip/roundtrip01-27.json | 用户测试源 | 是（27 项） | 独立往返用例：解析+序列化比对；但 0.9.97 哈希表无法对含指针成员结构（Obj3）构造（见下） |
| Tests/Common.hpp | 框架头（测试公共设施） | 否 | 测试基架：test_base/processFilesInFolder/benchmark 结构 |
| Tests/Jsonifier.hpp、Glaze.hpp、Simdjson.hpp | 基准库适配头 | 否 | 基准对比代码（jsonifier/glaze/simdjson 三库桥接），非用例 |
| Tests/Canada.hpp、CitmCatalog.hpp、Discord.hpp、Twitter.hpp、UnicodeEmoji.hpp | 样例数据（真实 JSON 数据集头） | 否 | 基准用样例数据集，非独立用例（main.cpp 中作 benchmark 输入） |
| Tests/GenerateGraphs.py、GetCommitHash.cmake | 脚本/辅助 | 否 | 图表生成与 commit 哈希辅助脚本 |
| Tests/ReadMe.mdWindows-MSVC.md | 文档 | 否 | MSVC 构建说明 |

## 二、运行结果（OHOS aarch64 工具链，适配补丁后头文件）

统计口径：
- 全目录发现独立上游用例总数：**69（float）+ 59（int）+ 43（uint）+ 9（string）+ 31（conformance）+ 27（roundtrip）= 238**
- 实际运行：**211**（float/int/uint/string/conformance）
- 不可运行：**27**（roundtrip，编译期哈希表构造限制）

| 测试组 | 独立用例数 | 实际运行 | 通过 | 失败 | 全量通过率 |
|---|---|---|---|---|---|
| FloatValidation | 69 | 69 | 69 | 0 | 69/69 = 100% |
| IntValidation | 59 | 59 | 59 | 0 | 59/59 = 100% |
| UintValidation | 43 | 43 | 43 | 0 | 43/43 = 100% |
| StringValidation | 9 | 9 | 9 | 0 | 9/9 = 100% |
| ConformanceTests | 31 | 31 | 31 | 0 | 31/31 = 100% |
| RoundTrip | 27 | 0 | 0 | 0 | 0/27 = 0%（硬阻塞） |
| **合计** | **238** | **211** | **211** | **0** | **211/238 = 88.66%** |

实际执行通过率（仅实际运行组）：211/211 = 100%

## 三、未运行/不可运行项详细原因

### RoundTrip（27 项，全部硬阻塞）

- **首错**：`HashMap.hpp:629: static assertion failed: 'constructionData.type != hash_map_type::unset': Failed to construct that hashmap!`
- **完整错误**：`collectMapConstructionData<round_trip_tests::Obj3>` 返回 `hash_map_type::unset` → `static_assert` 失败；次错 `HashMap.hpp:682: variable has incomplete type 'const void'`
- **根因**：0.9.97 上游编译期哈希表（compile-time hash map）无法为含 `std::unique_ptr`/裸指针成员的结构（RoundTrip 的 Obj3）构造键统计——哈希表构造依赖反射出的键长度分布，指针成员不满足任一哈希策略分支。
- **验证**：最小复现（仅含 Obj3 形态结构 + `jsonifier::core` 注册）在补丁头与未修补原始头下均同错（原始头在 immintrin 处先行失败属另一平台问题，隔离该头后同一 static_assert 复现），**与 OHOS 适配补丁无关，属上游 0.9.97 缺陷**。
- **命令**：`/data/service/hnp/bin/clang++ -std=c++2b -O0 -w -DJSON_TEST_PATH=/storage/Users/currentUser/zhouyu/build_in_harmonyos-jsonifier-0.9.97/.build-cache/jsonifier-src/Jsonifier-0.9.97/Tests/ -I /storage/Users/currentUser/tmp/jsonifier-probe/patched -I /storage/Users/currentUser/tmp/jsonifier-uptests run_roundtrip.cpp -o run_roundtrip` → exit 1
- **恢复条件**：上游修复 RoundTrip 用例结构（去除指针成员）或 jsonifier 支持指针成员哈希构造（更高版本可能已支持），非当前库适配补丁范围。
- **归类**：上游用例缺陷导致的编译期阻塞（非本库编译/配方错误）。

### RoundTrip 27 项逐项回报（入口 / 分类 / 命令 / cwd / 退出码 / 首条错误 / 技术原因 / 受影响入口 / 恢复条件）

公共执行环境（适用于全部 27 项，r06 实测重验 2026-09-06 02:13）：
- **命令**：`/data/service/hnp/bin/clang++ -std=c++2b -O0 -w -DJSON_TEST_PATH=/storage/Users/currentUser/zhouyu/build_in_harmonyos-jsonifier-0.9.97/.build-cache/jsonifier-src/Jsonifier-0.9.97/Tests/ -I /storage/Users/currentUser/tmp/jsonifier-probe/patched -I /storage/Users/currentUser/tmp/jsonifier-uptests run_roundtrip.cpp -o run_roundtrip`
- **cwd**：`/storage/Users/currentUser/tmp/jsonifier-uptests/`（驱动源 run_roundtrip.cpp 所在目录）
- **退出码**：1（编译失败，未到运行阶段）
- **首条错误**：`HashMap.hpp:629: static assertion failed: 'constructionData.type != hash_map_type::unset': Failed to construct that hashmap!`（由 roundtrip10 的 Obj3 实例化链触发）
- **技术原因**：RoundTrip.hpp 的 `roundTripTests()` 内全部 27 个 `runTest<类型>` 调用在**同一翻译单元**实例化；roundtrip10 目标类型 `Obj3`（含 `std::unique_ptr<int32_t>` 与 `std::string*` 指针成员）触发编译期哈希表构造失败 → 整个 TU 编译中断，27 项全部不可编译，非逐项独立失败。
- **恢复条件**：上游将 Obj3 改为无指针成员结构，或 jsonifier 支持指针成员哈希构造；当前库适配补丁无法在不改上游用例语义的前提下恢复该项。

| # | 入口（数据文件） | runTest 目标类型 | 分类 | 受影响入口 | 备注 |
|---|---|---|---|---|---|
| 1 | RoundTrip/roundtrip01.json | `std::vector<int32_t*>` | 独立往返用例 | roundtrip01 | 同 TU 编译阻塞 |
| 2 | RoundTrip/roundtrip02.json | `std::vector<bool>` | 独立往返用例 | roundtrip02 | 同 TU 编译阻塞 |
| 3 | RoundTrip/roundtrip03.json | `std::vector<bool>` | 独立往返用例 | roundtrip03 | 同 TU 编译阻塞 |
| 4 | RoundTrip/roundtrip04.json | `std::vector<int32_t>` | 独立往返用例 | roundtrip04 | 同 TU 编译阻塞 |
| 5 | RoundTrip/roundtrip05.json | `std::vector<std::string>` | 独立往返用例 | roundtrip05 | 同 TU 编译阻塞 |
| 6 | RoundTrip/roundtrip06.json | `std::vector<int32_t>` | 独立往返用例 | roundtrip06 | 同 TU 编译阻塞 |
| 7 | RoundTrip/roundtrip07.json | `std::unordered_map<std::string, std::string>` | 独立往返用例 | roundtrip07 | 同 TU 编译阻塞 |
| 8 | RoundTrip/roundtrip08.json | `std::vector<int32_t>` | 独立往返用例 | roundtrip08 | 同 TU 编译阻塞 |
| 9 | RoundTrip/roundtrip09.json | `Obj2`（`std::string foo`） | 独立往返用例 | roundtrip09 | 同 TU 编译阻塞 |
| 10 | RoundTrip/roundtrip10.json | **`Obj3`（`std::unique_ptr<int32_t>`+`std::string*`）** | 独立往返用例 | roundtrip10 | **触发首错根因**：指针成员哈希构造失败 |
| 11 | RoundTrip/roundtrip11.json | `std::vector<int32_t>` | 独立往返用例 | roundtrip11 | 同 TU 编译阻塞 |
| 12 | RoundTrip/roundtrip12.json | `std::vector<int32_t>` | 独立往返用例 | roundtrip12 | 同 TU 编译阻塞 |
| 13 | RoundTrip/roundtrip13.json | `std::vector<int64_t>` | 独立往返用例 | roundtrip13 | 同 TU 编译阻塞 |
| 14 | RoundTrip/roundtrip14.json | `std::vector<int64_t>` | 独立往返用例 | roundtrip14 | 同 TU 编译阻塞 |
| 15 | RoundTrip/roundtrip15.json | `std::vector<int32_t>` | 独立往返用例 | roundtrip15 | 同 TU 编译阻塞 |
| 16 | RoundTrip/roundtrip16.json | `std::vector<int32_t>` | 独立往返用例 | roundtrip16 | 同 TU 编译阻塞 |
| 17 | RoundTrip/roundtrip17.json | `std::vector<int64_t>` | 独立往返用例 | roundtrip17 | 同 TU 编译阻塞 |
| 18 | RoundTrip/roundtrip18.json | `std::vector<int64_t>` | 独立往返用例 | roundtrip18 | 同 TU 编译阻塞 |
| 19 | RoundTrip/roundtrip19.json | `std::vector<int64_t>` | 独立往返用例 | roundtrip19 | 同 TU 编译阻塞 |
| 20 | RoundTrip/roundtrip20.json | `std::vector<double>` | 独立往返用例 | roundtrip20 | 同 TU 编译阻塞 |
| 21 | RoundTrip/roundtrip21.json | `std::vector<double>` | 独立往返用例 | roundtrip21 | 同 TU 编译阻塞 |
| 22 | RoundTrip/roundtrip22.json | `std::vector<double>` | 独立往返用例 | roundtrip22 | 同 TU 编译阻塞 |
| 23 | RoundTrip/roundtrip23.json | `std::vector<double>` | 独立往返用例 | roundtrip23 | 同 TU 编译阻塞 |
| 24 | RoundTrip/roundtrip24.json | `std::vector<double>` | 独立往返用例 | roundtrip24 | 同 TU 编译阻塞 |
| 25 | RoundTrip/roundtrip25.json | `std::vector<double>` | 独立往返用例 | roundtrip25 | 同 TU 编译阻塞 |
| 26 | RoundTrip/roundtrip26.json | `std::vector<double>` | 独立往返用例 | roundtrip26 | 同 TU 编译阻塞 |
| 27 | RoundTrip/roundtrip27.json | `std::vector<double>` | 独立往返用例 | roundtrip27 | 同 TU 编译阻塞 |

**独立证据**：`/storage/Users/currentUser/tmp/jsonifier-uptests/rt_compile3_r06.txt`（roundtrip 编译完整错误链，SHA-256=0e86ede75ca41a4632467cd13e4aa40813f9153de9003aa8c16913836c458bd6）；`hm_probe.cpp` 最小复现（Obj3 形态哈希构造，补丁头/原始头同错）——见 `/storage/Users/currentUser/tmp/jsonifier-uptests/hm_err.txt`（SHA-256=834ff3f7016fd05c7aab4ddf23f77071534a8c4ea3ba3c73bffb2cbf794044ff）与 `hm_orig.txt`（SHA-256=d32f1da364e620b107ad5876d97db27e68a0f91fb3e96f1682bfb67392a8707b）。

## 四、验证证据（r06 严格重采，2026-09-06 02:13）

公共编译器：`/data/service/hnp/bin/clang++`（OHOS SDK clang-15.0.4，aarch64）；公共 cwd：`/storage/Users/currentUser/tmp/jsonifier-uptests/`；公共 include：`-I /storage/Users/currentUser/tmp/jsonifier-probe/patched -I /storage/Users/currentUser/tmp/jsonifier-uptests`；公共宏：`-DJSON_TEST_PATH=/storage/Users/currentUser/zhouyu/build_in_harmonyos-jsonifier-0.9.97/.build-cache/jsonifier-src/Jsonifier-0.9.97/Tests/`（宏值带引号包裹，实测编译通过）。

实际运行组（compile exit=0，run exit=0）：

| 组 | 编译命令 | 运行命令 | 首条 stdout | 日志路径 | SHA-256 |
|---|---|---|---|---|---|
| float（69 用例，138 行 Succeeded） | `/data/service/hnp/bin/clang++ -std=c++2b -O0 -w -D'JSON_TEST_PATH="/storage/Users/currentUser/zhouyu/build_in_harmonyos-jsonifier-0.9.97/.build-cache/jsonifier-src/Jsonifier-0.9.97/Tests/"' -I /storage/Users/currentUser/tmp/jsonifier-probe/patched -I /storage/Users/currentUser/tmp/jsonifier-uptests run_float.cpp -o run_float` | `./run_float` | `Float Tests: / test1.json Input: [0.0] / test1.json Succeeded - Output: 0` | `/storage/Users/currentUser/tmp/jsonifier-uptests/float_r06.out` | `2f62a33957c299587c33eb9a0944cb7821634e7ff52f1f8c0d74d3c41cfa4ae2` |
| int（59 用例） | `/data/service/hnp/bin/clang++ -std=c++2b -O0 -w -D'JSON_TEST_PATH="/storage/Users/currentUser/zhouyu/build_in_harmonyos-jsonifier-0.9.97/.build-cache/jsonifier-src/Jsonifier-0.9.97/Tests/"' -I /storage/Users/currentUser/tmp/jsonifier-probe/patched -I /storage/Users/currentUser/tmp/jsonifier-uptests run_int.cpp -o run_int` | `./run_int` | `Int Tests: / Integer-Pass-Test 0 Input: 0 / Integer-Pass-Test 0 Succeeded - Output: 0` | `/storage/Users/currentUser/tmp/jsonifier-uptests/int_r06.out` | `a038a3e86b54f785382c9fcb6ca34cb01d1d5a9e501b76abd26919b35fe1351e` |
| uint（43 用例） | `/data/service/hnp/bin/clang++ -std=c++2b -O0 -w -D'JSON_TEST_PATH="/storage/Users/currentUser/zhouyu/build_in_harmonyos-jsonifier-0.9.97/.build-cache/jsonifier-src/Jsonifier-0.9.97/Tests/"' -I /storage/Users/currentUser/tmp/jsonifier-probe/patched -I /storage/Users/currentUser/tmp/jsonifier-uptests run_uint.cpp -o run_uint` | `./run_uint` | `Uint Tests: / Unsigned-Integer-Pass-Test 1 Input: 0 / Unsigned-Integer-Pass-Test 1 Succeeded - Output: 0` | `/storage/Users/currentUser/tmp/jsonifier-uptests/uint_r06.out` | `cd8889ecf53ba5f16aa3e89e0b48c93a937582d81fa6670b32ba395ea8a42957` |
| string（9 用例，18 行 Succeeded） | `/data/service/hnp/bin/clang++ -std=c++2b -O0 -w -D'JSON_TEST_PATH="/storage/Users/currentUser/zhouyu/build_in_harmonyos-jsonifier-0.9.97/.build-cache/jsonifier-src/Jsonifier-0.9.97/Tests/"' -I /storage/Users/currentUser/tmp/jsonifier-probe/patched -I /storage/Users/currentUser/tmp/jsonifier-uptests run_string.cpp -o run_string` | `./run_string` | `String Tests: / test1.json Input: "" / test1.json Succeeded - Output:` | `/storage/Users/currentUser/tmp/jsonifier-uptests/string_r06.out` | `7407530d3686eecc9d44cb337ee96f1f53ae22a923f6b3d2c94eab75b1c94505` |
| conformance（31 用例） | `/data/service/hnp/bin/clang++ -std=c++2b -O0 -w -D'JSON_TEST_PATH="/storage/Users/currentUser/zhouyu/build_in_harmonyos-jsonifier-0.9.97/.build-cache/jsonifier-src/Jsonifier-0.9.97/Tests/"' -I /storage/Users/currentUser/tmp/jsonifier-probe/patched -I /storage/Users/currentUser/tmp/jsonifier-uptests run_conformance.cpp -o run_conformance` | `./run_conformance` | `Conformance Tests: / Running Test: fail02.json / Test: fail02.json = Succeeded 02` | `/storage/Users/currentUser/tmp/jsonifier-uptests/conformance_r06.out` | `fa6a33b7fcbf25361b0b3f733d6448eab03aba39f826b49c9b30dc0ddb2272b1` |

未运行组（roundtrip，27 个入口，同 TU 编译中断，compile exit=1）：
- 编译命令：`/data/service/hnp/bin/clang++ -std=c++2b -O0 -w -D\'JSON_TEST_PATH="/storage/Users/currentUser/zhouyu/build_in_harmonyos-jsonifier-0.9.97/.build-cache/jsonifier-src/Jsonifier-0.9.97/Tests/"\' -I /storage/Users/currentUser/tmp/jsonifier-probe/patched -I /storage/Users/currentUser/tmp/jsonifier-uptests run_roundtrip.cpp -o run_roundtrip`
- 退出码：1；首错：`HashMap.hpp:629: static assertion failed due to requirement 'constructionData.type != hash_map_type::unset': Failed to construct that hashmap!`；次错：`HashMap.hpp:682: variable has incomplete type 'const void'`（错误总数 2）
- 日志：`/storage/Users/currentUser/tmp/jsonifier-uptests/rt_compile3_r06.txt`，SHA-256=`0e86ede75ca41a4632467cd13e4aa40813f9153de9003aa8c16913836c458bd6`

- 编译器：`/data/service/hnp/bin/clang++`（OHOS SDK clang-15.0.4，aarch64），`-std=c++2b`
- 数据目录：上游 `Tests/`（JSON_TEST_PATH 指向）
- SHA-256：上游源码 tar 859a90731c5623e4cb4200bfa7b5dcb32d75f019147b06f73b7ecc0eec31b231（台账数据均来自该 tar 解压目录）

## 五、统计口径说明

- 分母=全量发现独立用例 238（含不可运行的 roundtrip 27，符合"未运行、不可运行、硬阻塞计入分母但不计为通过"）
- 若仅按实际运行组统计：211/211 = 100%（供参考，不作为全量通过率）
- 框架头/样例数据/基准程序（Common.hpp、各数据集头、main.cpp）均不误算为独立用例，但已在第一部分逐项列出
