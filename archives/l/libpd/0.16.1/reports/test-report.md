# libpd 0.16.1 测试报告

- 目标平台：OpenHarmony PC aarch64（`aarch64-unknown-linux-ohos`）
- 编译器：OHOS clang 15.0.4；Conan 2.29.1；CMake 4.1.2
- 测试日期：2026-09-15
- 最终 SHA：见 PR 正文与 `reports/conan-verify-report.md`

## 计数口径

`TOTAL = PASS + FAIL + SKIP + NOT_RUN`；计数单位是**测试用例**（框架注册的
`@Test` / `[Test]` 各算 1 个用例；无框架的独立 assert 程序整体算 1 个用例）。
四种口径（源码宏数 / 框架注册数 / assertion 数 / 消费者断言数）**不混用**：
本报告只申报用例数这一个口径，不另立 assertion 调用点计数（第二个口径必须与
用例数同源可复算，否则易多报）；仅在识别"该程序是否含断言"时引用两处 C 程序
的 assert 调用点数。上游表与适配后表使用同一单位。

## 上游测试清点（N = 上游测试用例总数 = 84）

清点结论：**N = 84，N′（本次实际运行）= 0**。逐项清单与"未运行"技术原因：

| # | 上游测试入口 | 框架/形态 | 用例数 | 实际运行 |
|---|-------------|----------|-------|---------|
| 1 | `samples/java/test/org/puredata/core/PdBaseTest.java` | JUnit 4 `@Test` | 16 | 0（NOT_RUN） |
| 2 | `samples/java/test/org/puredata/core/utils/PdDispatcherTest.java` | JUnit 4 `@Test` | 3 | 0（NOT_RUN） |
| 3 | `samples/csharp/pdtest/`（13 个 `*Tests.cs`） | NUnit `[Test]` | 63 | 0（NOT_RUN） |
| 4 | `samples/c/pdtest_thread/pdtest_thread.c` | 裸 `assert.h` 程序 | 1 | 0（NOT_RUN） |
| 5 | `samples/c/pdtest_queued/pdtest_queued.c` | 裸 `assert.h` 程序 | 1 | 0（NOT_RUN） |
| | **合计** | | **84** | **0** |

C# 逐文件用例数：`LibPDTests.cs` 7、`Managed/{Audio 5, CApi 2, Messaging 8, Midi 7,
Patch 3, PdArray 5, Pd 7}`、`MultiInstance/{Audio 1, Messaging 6, Midi 5, PdArray 3,
PdNumberOfInstances 4}`。

**逐项未运行的技术原因**（按 R51「未运行项必须逐条给技术原因」）：

1. **JUnit（19 个用例）**：需要 JVM + JUnit 4 + EasyMock/Objenesis + 由 `jni/` 构建的
   `libpdnative`（JNI 绑定）。OHOS 目标上不存在该运行时；上游 CI 也完全未触及 `samples/java`。
2. **NUnit（63 个用例）**：需要 .NET/Mono + NUnit + 通过 P/Invoke 调用 libpd 共享库；
   OHOS 目标无 .NET 运行时；上游 CI 完全未触及 `samples/csharp`。
3. **`samples/c/pdtest_thread`（1 个用例/17 处 assert）**：该程序走多实例 API
   （`:54` `libpd_new_instance()`、`:196` `assert(result == expected && "DSP results are wrong")`），
   其自带 Makefile 以 `make MULTI=true` 构建 libpd。本配方沿用**上游默认**
   `PD_MULTI=OFF`（Makefile `MULTI` 未设、CMake `PD_MULTI=OFF`），此时
   `libpd_new_instance()` 返回 NULL（`libpd_wrapper/z_libpd.c`），程序必然在 `:54` 失败——
   即它测的是本包未交付的构建变体。上游 CI 只**编译**它，从不运行。
4. **`samples/c/pdtest_queued`（1 个用例/3 处 assert）**：同样需要 `PDINSTANCE`/`PDTHREADS`
   （`libpd_new_instance` + `libpd_queued_init`，`:117` assert `pthread_create` 成功）；
   限制同第 3 条。上游 CI 只编译，不运行。

### 上游断言型入口的穷尽性证据（避免漏报）

| 清点对象 | 命令 | 结果 |
|---|---|---|
| 全仓测试框架标记 | `grep -rln "TEST_CASE\|TEST_F\|BOOST_AUTO_TEST\|\[Test\]\|\[Fact\]\|@Test\|unittest\|def test_\|assert(" . --exclude-dir=pure-data` | 命中 **20** 个文件 = 上表 1-5 的 17 个文件（2 Java + 13 C# + 2 C）+ `jni/oboe/logging_macros.h`（第三方 Oboe 日志宏，1 处 assert）+ `samples/cpp/pdtest_freeverb/src/RtAudio.cpp` 与 `samples/cpp/pdtest_rtaudio/src/RtAudio.cpp`（**vendored 第三方 RtAudio**，各 2 处 assert）。后 3 个文件非 libpd 测试，已排除，故无未申报入口 |
| 目录清点 | `find . -type d -iname "*test*"` | 无 `tests/`；只有 `samples/**` 下的示例目录与 `samples/java/test` |
| CMake 注册 | `grep -n "enable_testing\|add_test\|ctest" CMakeLists.txt` | 0 处命中 |
| Makefile 目标 | `grep -n "^check\|^test" Makefile` | 无（`.PHONY: libpd csharplib javalib javadoc javasrc install uninstall clean clobber`） |
| 上游 CI 运行步骤 | `.github/workflows/builds.yaml`（该文件不在 GitHub 归档包内，经 GitHub API `contents/.github/workflows?ref=0.16.1` 对 tag 0.16.1 核对存在） | 只 `make -C samples/c/pdtest`、`pdtest_multi`、`pdtest_thread` **编译**，无任何运行/断言步骤；未触及 java/csharp |
| pure-data 子模块（pin `f009fd8d`） | `grep -n "TESTS" pure-data/Makefile.am`；`find pure-data -maxdepth 1 -iname "test*"` | 无 `TESTS` 声明、无 `test/` 目录；`pure-data/libpd/test_libpd/test_libpd.c` 是双实例演示（打印 tick、恒 `return 0`、无断言），`gtk/test1.pd` 是演示 patch |

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试（JUnit + NUnit 绑定测试） | 82 | `samples/java/test`（19）+ `samples/csharp/pdtest`（63） |
| 集成测试（无框架 assert 程序） | 2 | `samples/c/pdtest_thread`、`samples/c/pdtest_queued` |
| 其他测试 | 0 | `samples/c` 其余 5 个、`samples/cpp`、`emscripten`、`objc`、`python` 均无断言 |
| **合计** | **84** | |

## 适配后测试统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 82 | 不变 | 上游 82 个绑定用例在 OHOS 目标上 **NOT_RUN**（无 JVM/.NET/JNI 运行时，上游 CI 亦不运行） |
| 集成测试 | 2 | 不变 | 上游 2 个裸 assert 程序 **NOT_RUN**（需 `PD_MULTI=true`，本配方随上游默认 OFF） |
| 鸿蒙特有测试 | 16 | 新增 | `test_package/libpd_test.c` 消费者断言（真实 C API 调用 + 真实 DSP 处理，不计入上游分母） |
| **合计** | **100** | **+16** | 上游合计 84 + 鸿蒙特有测试 16；上游部分全部 NOT_RUN，逐项原因见上 |

消费者断言明细（`test_package/libpd_test.c`，全部 PASS）：

1. `libpd_init()` 返回 0
2. `libpd_init()` 打印 Pure Data 版本横幅
3. 横幅中的 pure-data 快照版本为固定的 0.56.5（防止交付物与源码快照不一致）
4. `libpd_init_audio(1, 2, 44100)` 接受该配置
5. `libpd_blocksize() == 64`
6. `libpd_openfile()` 打开夹具 patch
7. 打开的 patch dollar-zero 有效
8. `libpd_exists("libpdtest") == 1`
9. `libpd_bang()` 到达接收者
10. bang 往返打印出期望值（`libpdtest: 42`）
11. `libpd_float()` 到达接收者
12. float 往返打印出期望值（`libpdtestfloat: 3.5`）
13. `libpd_finish_message("pd", "dsp")` 成功开启 DSP
14. 100 个音频块的输出样本全部有限（无 NaN/Inf）
15. `[osc~ 440] -> [dac~]` 链路产生可听幅度（峰值 > 0.1）
16. 输出峰值不超过 1.0

## 结果

| 指标 | 数值 |
|------|------|
| 上游测试通过率 | 0/84（0.0——84 个上游用例在 OHOS 目标上全部 NOT_RUN，逐项技术原因见上） |
| 新增测试通过率 | 16/16（100.0%） |
| `conan create` | rc=0（`shared=True` 与 `shared=False` 两种形态各验证一次） |
| W3 本地 CI 门禁 | L0 pass / L1 pass（含 L1e 破坏性反向验证）/ L2 skip（无 bin/）/ L4 pass / L5 pass |
| 上游 PASS / FAIL / SKIP / NOT_RUN | 0 / 0 / 0 / 84 |

## 门禁补测（`conan-verify` G4/L2/L4/L5 路径解析缺陷）

`conan-verify` 的 G4/L2/L4/L5 取程序包 ID 时解析失败（报 `无法找到程序包 ID`、
`跳过（无 cache 路径）`），四项会静默并列 `✅ PASS`。按 notes/device-facts.md §7.2
人工补测，结论如下（完整证据见 `reports/conan-verify-supplement.md`）：

| 门禁 | 补测内容 | 结果 |
|------|---------|------|
| G4 | 包内产物清单 ↔ `package_info()` | 10 个头文件（`include/libpd/` 与 `include/libpd/util/`）+ `lib/libpd.so`，与 `libs=["pd"]`/`libdirs=["lib"]`/`includedirs` 一致 |
| L2 | 用**打包后的** `libpd.so` 重编并运行消费者程序 | 16/16 PASS（`failures=0`）；`ctypes.CDLL` 加载成功，`libpd_blocksize()==64` |
| L4 | `readelf -h/-lW/-dW` | `ELF64 DYN AArch64`；`GNU_STACK RW`（NX）；`GNU_RELRO` 存在；`FLAGS: SYMBOLIC BIND_NOW` + `FLAGS_1: NOW`；无 `TEXTREL`/`RPATH`/`RUNPATH`；`NEEDED=libc.so`；`SONAME=libpd.so` |
| L5 | 两次独立构建产物比对 | 两份构建树（`conan-verify` G2 与 W3）的 `lib/libpd.so` 逐字节一致，聚合 sha256 `0ca6c9912eed4cbae80a202445cf0326f05883289450095bcdf41bdf723288f1`；产物未嵌入构建路径（`strings` 命中 0） |

首轮 L5a 曾报 `libpd.so 缺少 DT_SONAME`：上游 Makefile 不设置 SONAME，已在配方
`ADDITIONAL_LDFLAGS` 追加 `-Wl,-soname,libpd.so`（与安装文件名一致），复验后
`L5_RESULT=pass` 且 W3 日志中无任何 `[fail]` 行。

## 证据

以下日志位于包目录 `reports/`（被 `.gitignore` 覆盖，不入 PR），干净轮副本保存在
任务私有目录 `$TASK_DIR/evidence-<sha8>/`，三份均可用
`capture_evidence.py --verify` 复算：

- `reports/conan-create.log`（干净轮 `conan create` 日志，构建标志计数
  `run_make=5 / calling_build=2`，判读为 clean）
- `reports/conan-verify-report.md`（G0–G4 门禁报告）
- `reports/w3-local-ci.log`（W3 本地 CI 日志，含 L0–L5 结果行）
- `reports/conan-verify-supplement.md`（上述 G4/L2/L4/L5 人工补测明细）
