# xerces 3.3.0 适配笔记

## 上游与版本
- 上游：Apache Xerces-C++ 3.3.0（3.x 最新正式版；API 兼容 3.x，ABI 与旧 3.x 不兼容，应用须重编）
- 官方源：`https://archive.apache.org/dist/xerces/c/3/sources/xerces-c-3.3.0.tar.gz`
- sha256：`9555f1d06f82987fbb4658862705515740414fd34b4db6ad2ed76a2dc08d3bde`（与官方 `.sha256` 校验文件一致，archive 与 downloads 双源核对）
- 上游仓库：`https://github.com/apache/xerces-c`
- License：Apache-2.0
- 构建系统：CMake（`cmake_minimum_required(VERSION 3.12.0)`，默认 C++14；OHOS profile 的 `compiler.cppstd=17` 覆盖消费者侧，库侧沿用上游默认）
- 包名说明：任务要求包名为 `xerces`（目录 `archives/x/xerces/3.3.0`、分支 `feat/xerces-3.3.0`）；上游工程名与产物名保持 `xerces-c`（`libxerces-c.a`、`xerces-c::xerces-c`），`package_info` 如实声明，详见「包名与产物名」。

## 平台检测分析（关键）
xerces-c 的 CMake 平台判定全部走通用 `UNIX`/`WIN32`/`APPLE` 标志（`cmake/Xerces*.cmake` 各选择模块；`grep 'STREQUAL "Linux"'` 无命中），**没有** `CMAKE_SYSTEM_NAME STREQUAL "Linux"` 这类 OS 专属分派。因此：
- OHOS conan profile 把 `os=OHOS` 自动映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，xerces 在 HarmonyOS 名下走与 Linux 一致的 UNIX 通用分支，行为不变。
- 对比 nsync 等库（有 `STREQUAL "Linux"` → 误入 Linux futex 分支 → musl 报错），本库**无此坑**，无需强制改写 `CMAKE_SYSTEM_NAME`。

## 三个后端为何显式钉死
network/transcoder/message-loader 后端由各自 `cmake/Xerces*Selection.cmake` 按优先级自动探测（取候选列表第 0 个）。默认探测在构建机上不够确定性，且可能拉入未发布依赖（R36）：

| 后端 | 候选优先级 | 默认风险 | 显式钉定 |
|------|-----------|---------|---------|
| network-accessor | curl → socket → winsock → cfurl | UNIX 上若 `find_package(CURL)` 命中会选 curl，拉入未发布的 curl 依赖 | `socket`（原生 BSD socket + getaddrinfo，musl libc 内置） |
| transcoder | icu → gnuiconv → iconv → … | 若 `ICU_FOUND` 会选 icu，拉入未发布的 ICU 依赖 | `gnuiconv`（libc iconv：iconv_open/iconv/iconv_close，musl 内置） |
| message-loader | inmemory → icu → iconv | 默认即 inmemory，但显式锁定避免被 ICU 探测覆盖 | `inmemory`（内置消息目录） |

ICU 本身非强制：`cmake/XercesICU.cmake` 仅 `find_package(ICU)`，缺失时静默忽略。但为避免构建机偶装 libcurl/ICU 导致探测漂移，三个后端一律显式钉到 libc-only 实现。

## pthread / iconv 依赖
- mutex-manager 默认 `standard`（C++ `std::thread`/`std::mutex`，由编译探测决定）；musl/libc++ 下 std::thread 底层走 pthread。
- musl 的 pthread、iconv、socket 符号**全部在 libc**，无独立 `libpthread`/`libiconv`/`libnsl`。因此静态库 `package_info` **不声明 system_libs**——链接时由 libc 自动解析。
- 若改为 glibc 目标才需 `-lpthread -ldl`，本目标仅 OHOS(musl) 故无需。

## 包名与产物名
- Conan 包名：`xerces`（任务指定）。
- 上游产物名：`libxerces-c.a`，CMake 包名 `xerces-c`、目标 `xerces-c::xerces-c`、pkg-config 名 `xerces-c`（上游 `project(xerces-c)` 决定，不随 Conan 包名改变）。
- `package_info` 设置 `libs = ["xerces-c"]` + `cmake_file_name / cmake_target_name / pkg_config_name` 均为 `xerces-c` 系，test_package 用 `find_package(xerces-c CONFIG REQUIRED)` + `target_link_libraries(... xerces-c::xerces-c)` 消费，与上游安装的 config 文件一致。

## 静态 vs 共享
- 默认 `BUILD_SHARED_LIBS=ON` 产 `libxerces-c-3.3.so.<ver>` + soname 软链（`cmake/XercesDLL.cmake`）。
- 本配方选**静态** `BUILD_SHARED_LIBS=OFF` 产 `libxerces-c.a`：
  - 静态产物最简单、依赖最少；
  - 规避 OHOS 共享库 SONAME/版本软链/签名链路等已知 CI 失败面；
  - 与 xerces-c 3.2.5 已合入库先例一致。

## samples 安装中和
- 顶层 `CMakeLists.txt` 无条件 `add_subdirectory(samples)`，samples/ 有 `install(TARGETS <sample exes> …)` 规则。OHOS 下 install-time 可执行重链接（CMakeRelink.dir）不受支持。
- `build()` 在 configure 后、build 前把生成的 `samples/cmake_install.cmake` 中和为空安装脚本（复用 3.2.5 已验证做法），`cmake --install` 仅交付库 + 头文件 + pkg-config。samples 可执行文件仍可编译（ctest 不依赖它们），但不安装、不发布。

## 上游测试审计（2026-09-20 按 v3.3.0 tag 逐文件重审，修正 35/19 旧数）
- 位置：`tests/` + `samples/`（`tests/CMakeLists.txt` + `samples/CMakeLists.txt` + `cmake/RunTest.cmake` wrapper，对比观测日志与 `expected/*.log`，时序已归一化）。`ctest` 在构建根执行，两目录用例全注册，旧审计只数了 `tests/` 是错的。
- 总数：**80**（与官方口径一致，`upstream_test_total: 80 / ctest_entries`）。
  - `tests/CMakeLists.txt`：`add_xerces_test` 字面 35 + 条件 `Char16Test` 1 项（`if(XERCES_XMLCH_T STREQUAL "char16_t")`；默认 `xmlch-type` 取 `char16_t`，OHOS clang 支持 → 注册，`tests/` 共 36）。
  - `samples/CMakeLists.txt`：`add_xerces_sample_test` 共 **44** 项（SAXCount 4、SAXPrint 4、SAX2Count 4、SAX2Print 6、MemParse 2、Redirect 2、DOMCount 4、DOMPrint 6、StdInParse 3、PParse 3、EnumVal 2、SEnumVal 2、CreateDOMDocument 1、SAXPrintLong 1）。
  - DOMTest、DOMMemTest、RangeTest、DOMTraversalTest（4）+ XSerializerTest 系 6（基项 EXPECT_FAIL）+ XSValueTest 1 + InitTermTest 系 4（基项 EXPECT_FAIL）+ ThreadTest 系 16（基项 EXPECT_FAIL；编号项各 `-threads 10 -time 20`）+ MemHandlerTest 系 3（基项 EXPECT_FAIL）+ DOMTypeInfoTest 1（`WORKING_DIRECTORY=src/DOM/TypeInfo`，wrapper 已处理）+ Char16Test 1。
- 运行：`build()` 先全量构建（含测试可执行文件），再执行 `ctest --output-on-failure --no-tests=error -E "^ThreadTest"`，即 64 项（tests/ 20 + samples/ 44）。
- 排除的 16 项 ThreadTest：每项 10 线程 × 20 秒（合计 300 秒以上），为吞吐量压力测试且对调度时序敏感，不适合单作业（`tools.build:jobs=1`）的共享 OHOS worker；tests/ 功能 + samples/ 回归共 64 项已全覆盖。排除项在 HMBS 标记的 `excluded_cases/excluded_count/reason` 中如实声明，不计入通过率。
- 防假绿：
  - `UPSTREAM_EXECUTED_CASES = 64` 硬断言：ctest 实际总数不符即抛错（上游增删用例时先审计再更新，不静默放行）。
  - 解析 `"% tests passed, % tests failed out of %"` 汇总行；缺失时回退计数 `Test #N: ... Passed/Failed` 行（Passed 行数 → passed，Failed|Timeout 行数 → failed，两计数器独立来源，不做减法修补）；`passed+failed==total` 恒等式不满足、总数为 0、失败非 0、退出码非 0 均判 `failed` 并抛错。
  - 取证：`HMBS_UPSTREAM_TEST_RESULT` 双通道输出（`print` + `self.output.info`），持久化 `build_folder/upstream_test_result.json` 并随包发布到 `res/`，test_package 逐轮原文重发（conan 缓存命中跳过 build() 时仍有证据）。

## test_package（消费者视角）
- `test.cpp`：真实调用 Xerces-C++ DOM API——`XMLPlatformUtils::Initialize` → `XercesDOMParser` + `MemBufInputSource` 解析内存 XML → 遍历 DOM 断言（无错误、文档非空、根标签 `root`、2 个子元素、首个文本 `hello`），共 6 断言；每断言打印 `CHECK PASS/FAIL` 行，终行打印 `OK (6/6 assertions)`。
- 生命周期：RAII 守卫保证 `Terminate()` 在所有 Xerces 对象析构后执行、且 parse/转码抛异常时仍执行（3.2.5 合入版本的同款守卫）。
- `conanfile.py test()`：运行 `./test_xerces` 并捕获日志，数 `CHECK PASS` 行得 `passedCount`，`discovered=6`；输出 `HMBS_TEST_PACKAGE_RESULT`；再读取包内 `res/upstream_test_result.json` 原文重发 `HMBS_UPSTREAM_TEST_RESULT`（缺失即抛错，不伪造）。

## 编译步骤
```bash
conan create archives/x/xerces/3.3.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
关键配置：`-DBUILD_SHARED_LIBS=OFF -Dnetwork-accessor=socket -Dtranscoder=gnuiconv -Dmessage-loader=inmemory`；单作业构建；构建后跑 64 项 ctest（-E "^ThreadTest"）；中和 samples 安装脚本后 `cmake --install`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | samples 安装阶段 CMakeRelink.dir 在 OHOS 不受支持 | samples/ 的 install(TARGETS) 在 install-time 触发可执行重链接 | 中和生成的 samples/cmake_install.cmake，仅交付库与头文件（复用 3.2.5 验证做法） |
| 2 | 后端探测可能随构建机环境漂移（curl/ICU） | Selection 模块按优先级自动探测 | 三个后端显式钉到 libc-only（socket/gnuiconv/inmemory），R36 零外部依赖 |
| 3 | ThreadTest 16 项在单作业 worker 上耗时过长（300 秒以上）且时序敏感 | 每项 `-threads 10 -time 20` 的压力测试 | `ctest -E "^ThreadTest"` 排除并在标记/notes/MANIFEST 三处声明，64 项（tests/ + samples/）全跑 |
| 4 | conan 缓存命中时 build() 被跳过导致上游证据缺失 | `conan create` 对已安装包跳过 build | 证据持久化到包内 `res/upstream_test_result.json`，test_package 逐轮重发 |

## 依赖版本
- 无外部 Conan 依赖（libc-only 后端；musl pthread/iconv/socket 在 libc 内）。

## 验证结果
- `conan create`（OHOS 真机预检）：待 HMBS 预检轮回填（ctest 64 项 + test_package 6 断言的实测数字以预检日志为准）。
- 本地（Windows）：仅完成配方静态检查（Python 语法编译 + YAML 解析），未运行 conan（按任务要求，不在本机运行 conan，真机验证由 HMBS 执行）。

## 交付物
| 文件 | 说明 |
|------|------|
| libxerces-c.a | 静态库 |
| include/xercesc/** | 公开头文件 |
| lib/pkgconfig/xerces-c.pc | pkg-config 元数据 |
| res/upstream_test_result.json | 上游 ctest 取证（供 test_package 重发） |

## 注意事项
- 本包 Conan 名 `xerces` 与上游产物名 `xerces-c` 的差异是任务指定的，如实记录；消费时一律用 `find_package(xerces-c)` + `xerces-c::xerces-c`。
- 上游测试通过率口径：64 项（tests/ 20 + samples/ 44；ThreadTest 16 项压力测试排除并声明，不计入分子分母）。
- Windows 检出注意：仓库同时存在 `archives/l/libXext` 与 `archives/l/libxext`（大小写仅差一字母），Windows 不区分大小写文件系统下二者冲突为同一目录，`git status` 会显示其 README/manifest 被“修改”；另 `archives/g/gama/.../0002-...patch??` 文件名含回车无法检出。二者均为环境产物，与本 PR 无关，本 PR 仅含 `archives/x/xerces/` 新增文件。

## 2026-09-20 真机 configure 失败两轮诊断
- 首轮预检指纹：CMakeLists.txt:58 project() 处 CMAKE_C/CXX_COMPILER 自检失败 + System unknown to cmake（cmake 4.4.3 无 Platform/HarmonyOS 模块）。
- 第一轮按 E266 补 SDK llvm/lib 经 LD_LIBRARY_PATH（主包 + test_package，固定路径 + glob + os.environ 双保险，configure 失败输出 CMakeError.log 尾部），复检同指纹复现（行号 100->147 证明新树已测），证伪 lld 缺库假设。
- 本轮改按 E092 在主包与 test_package 的 CMakeToolchain 中以 cache_variables 设 CMAKE_SYSTEM_NAME=Linux + PROCESSOR（armv8->aarch64，R32 口径）；xerces 仅用通用 UNIX 分支且无 STREQUAL Linux 分派，别名不改变上游行为；LD 兜底与诊断保留。测试口径不变（19 功能用例 + 6 断言）。

## 2026-09-20 第四轮（第 2 策略周期）：减法对齐，停用环境叠加假设
- 前三轮（E266 LD 兜底 → E092 cache 别名 → bare-compiler smoke 取证）同一指纹连续复现，按规则判环境假设家族 exhausted：行号递增证明新树已测，但摘要始终停在 `compiler identification is unknown` 且无真实 stderr，说明叠加层未提供新证据。
- 上一方案为何无效：① profile 已自带 SDK llvm/lib 的 LD_LIBRARY_PATH，配方内重复 prepend 只能漂移；② `cache_variables` 与已合入 barrier-2.4.0/edlib-1.2.7 的 `variables` 形式存在不必要差异；③ bare-compiler smoke 不继承工具链 --target/--sysroot，直连失败会掩盖 CMake 真因；④诊断写死 `build/Release/build/Release` 双重路径，恒报 `toolchain found: NONE`，误导定位。
- 本轮换减法路线：删除 LD 兜底/smoke/硬编码诊断，主包与 test_package 统一为 barrier/edlib 验证式（`tc.variables` 设 SYSTEM_NAME=Linux + PROCESSOR + POLICY_MINIMUM=3.5），诊断改递归 glob 定位 conan_toolchain.cmake。测试口径不变（19 功能用例 + 6 断言）。改动保持未提交，待 HMBS 同步后复检 project() 是否通过或拿回真实 try-compile 文本。

## 2026-09-20 第五轮（同指纹第 3 次）：编译器存在性取证 + 缺失回退
- 前轮（减法对齐 variables 式）复检仍同指纹，但诊断首次完整：工具链文件被正常消费（`CMAKE_C_COMPILER=/data/service/hnp/bin/clang` 已写入）、全树无 `CMakeError.log/CMakeOutput.log`。无 try-compile 日志 + C/CXX 双双 unknown，说明失败在编译器文件存在/spawn 层，而非编译内容层。
- 此前各轮都默认编译器文件存在，从未验证该前提；本轮换新路线：只做观察性取证（isfile + bin 目录列表 + 无需 flags 的 `--version`，不做 bare 编译链接以免掩盖 try-compile），conf 路径缺失时才用 SDK llvm/bin 或 PATH 回退显式钉死 `CMAKE_C_COMPILER/CXX_COMPILER`，存在时保持 profile 权威不动。测试口径不变（19 功能用例 + 6 断言）。改动保持未提交，待 HMBS 同步后复检。

## 2026-09-20 第六轮（第 3 策略周期）：修正上游总数审计（35/19 → 80/64）
- 上一方案为何无效：编译链路已通（库 100% 构建成功，ctest 实际跑起来），失败是配方自检 `upstream ctest drift: ran 64 tests, audited 19 (total upstream 35, excluded 16)` 主动抛错。旧审计只数了 `tests/CMakeLists.txt` 的 `add_xerces_test`（35），漏了两处：① `ctest` 在构建根执行，`samples/CMakeLists.txt` 的 44 项 `add_xerces_sample_test` 同样注册（日志中 `DOMPrint5`/`StdInParse1` 即样品用例，不在 tests/ 内）；② `tests/` 内条件项 `Char16Test`（`XERCES_XMLCH_T STREQUAL char16_t`，OHOS clang 默认启用）。36 + 44 = 80 总数，减 16 ThreadTest = 64，与真机 `ran 64` 完全吻合。
- 本轮换审计修正路线（非环境假设）：按 v3.3.0 tag 逐文件重数（tests/ 36 + samples/ 44 = 80，见上节审计），`UPSTREAM_TOTAL/EXCLUDED/EXECUTED` 改为 80/16/64；回退计数改为 Passed/Failed 双独立来源 + `passed+failed==total` 恒等式自检；MANIFEST（80/ctest_entries + tests 20 + samples 44 分项）、manifest.yaml、notes 口径同步更新。构建逻辑与排除理由不变（仅 ThreadTest 压力排除）。改动保持未提交，待 HMBS 同步后复检 64 项是否全过。

## 2026-09-20 Seventh round: test_package reuses main-recipe compiler fallback (upstream 64/64 green)
- Comparison with previous round: the 80/16/64 audit fix took effect; the main package built 100% and upstream ctest passed 64/64 (preflight: discovered 64, executed 64, passed 64), so the old drift is gone. The new failure domain is test_package project() failing with CMAKE_CXX_COMPILER identification unknown (/data/service/hnp/bin/clang++), a different fingerprint from the main-package issue, so no audit change is repeated; this round aligns the toolchain instead.
- Root cause: test_package generate() only set the SYSTEM_NAME alias and lacked the main recipe's conf-compiler existence check plus missing-path fallback. The profile-declared hnp-bin compiler cannot complete identification on this worker, while the harmonybrew clang the main build fell back to is proven good; the two sides behaved inconsistently, so the library passed and the consumer failed.
- Change: test_package gains the same _conf_compilers/_fallback_compiler helpers in the same order (hnp bin, SDK llvm/bin, PATH); CMAKE_C/CXX_COMPILER is pinned explicitly only when the conf path is absent, otherwise profile authority is kept. Test scope unchanged (upstream 64 + own 6 assertions). Changes stay uncommitted pending HMBS sync and re-preflight of test_package configure.

## 2026-09-20 Eighth round: rule4 gaps declaration for 16 excluded ThreadTest cases
- Previous round: main build + ctest 64/64 + test_package 6/6 all green, but gate judged incomplete: upstream total is 80 while marker reported discovered/executed/passed 64 without a gaps array explaining the 16 unrun cases.
- Root cause: recipe-side omission, not a test regression. Total 80 = tests/ 36 (incl. Char16Test) + samples/ 44; 16 ThreadTest stress cases (each -threads 10 -time 20, 300+s total, timing-sensitive) excluded via ctest -E ^ThreadTest for the single-job (jobs=1) shared worker. Marker carried excluded_cases/count/reason but no gaps entry, so rule4 could not reconcile 80-64=16.
- Change: _run_upstream_ctest marker gains gaps=[{count:16, category:environment, detail, evidence}] (count constant = UPSTREAM_EXCLUDED_CASES; evidence cites tests/CMakeLists.txt -threads 10 -time 20 entries, HMBS_PLATFORM_CAPABILITIES jobs=1, preflight 64/64 log). test_package re-emits payload verbatim so cache-hit rounds keep the gaps. Test scope unchanged (64 run + 6 assertions). .hmbs/pr-body.md draft updated from stale 35/19 to 80/64 with the same exclusion statement. Changes stay uncommitted pending HMBS sync and re-preflight.
