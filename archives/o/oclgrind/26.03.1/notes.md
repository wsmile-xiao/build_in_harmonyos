# oclgrind 26.03.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-10
- 编译器: clang/clang++ (HarmonyOS PC 真机, aarch64)
- 状态: built (首轮工作树, 待 HMBS 真机预检)

## 上游信息
- 名称: Oclgrind (OpenCL device simulator and debugger)
- 版本: 26.03.1
- 仓库: https://github.com/jrprice/Oclgrind
- 源码: https://github.com/jrprice/Oclgrind/archive/refs/tags/v26.03.1.tar.gz
- 许可证: BSD-3-Clause
- 构建要求: LLVM/Clang >= 18.0 开发库与头文件, C++17, Python (测试), GNU readline (可选, 有历史记录的交互调试器)

## 上游测试清点 (v26.03.1 tag 审计)
- tests/kernels/TESTS: 90 个 kernel 仿真用例 (alignment 2 + async_copy 8 + atomics 13 + barrier 2 + bugs 14 + data-race 13 + interactive 2 + memcheck 11 + misc 10 + uninitialized 11 + wait_event 4), 由 tests/run_test.py + oclgrind-kernel 驱动, ctest 注册
- tests/runtime: 5 个 rt_* 用例 (build_program, kernel_scope_local_mem_usage, map_buffer, multqueues, sampler), 链接 oclgrind-rt, 由 oclgrind-exe 驱动
- tests/apps: 2 个 app_* 用例 (image, vecadd)
- 合计: 97 个 ctest 用例, 框架 ctest, 命令 ctest --output-on-failure
- 部分用例按 LLVM 版本标记 WILL_FAIL (XFAIL): LLVM 18 Windows 特例, LLVM <19 / >=21 的 interactive 指针用例, LLVM >=22 的 memcheck 静态数组用例

## 编译步骤

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DREADLINE_DIR=<readline包路径>
cmake --build build
ctest --output-on-failure
cmake --install build
```

配方通过 CMakeToolchain 传递 READLINE_DIR (来自 readline/8.3 依赖包路径), LLVM/Clang 由上游 CMake 的 find_package(LLVM REQUIRED CONFIG) 自动探测。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | LLVM >= 18.0 硬要求, 仓库 llvm/clang 仅 built 未发布, 系统 clang 为 15 | oclgrind 上游 CMake 在 LLVM_PACKAGE_VERSION < 18.0 时 FATAL; 真机 SDK 工具链版本不足 | 首轮配方不 vendor LLVM (1.7GB/数小时编译), 直接透出上游错误, 由真机预检给出机器证据后再定 env_unsupported 或补齐方案 |
| 2 | 仓库 llvm/20.1.0 与 llvm/22.1.0 均以 LLVM_ENABLE_PROJECTS="" 构建, 无 clang 前端库/头/opencl-c.h | 该 LLVM 包无法满足 oclgrind 的 clangCodeGen/clangFrontend/clang 头与 opencl-c.h 检查 | 不声明对仓库 llvm/clang 的 conan 依赖, 避免把不可用依赖写进配方 (R36/PF4), 改由 CMake 探测并如实报错 |
| 3 | oclgrind-rt 以 -Wl,-soname,libOpenCL.so 伪装系统 OpenCL | 与系统 libOpenCL 同名但为模拟器实现, 非系统库污染 | 保留 .so (非 R26 系统同名库情形), package_info 同时导出 libs 与 bindirs, commands.json 声明为 tool |
| 4 | 真机 source() 直连 github.com 两次 ConnectTimeout 后才成功 | 真机到 github.com 30s 连接超时, 属守则源码包下载超时例外 | conandata.yml 的 url 改为有序列表: gh-proxy.com 镜像 (ci/conan/build_and_test.sh 的 GitHub 映射) 在前、官方原 URL 最后回退, sha256 不变 |
| 5 | 真机 cmake 配置报 CMAKE_C_COMPILER/CXX_COMPILER (/data/service/hnp/bin/clang) broken | 默认 Unix Makefiles generator 硬编码 SHELL=/bin/sh, 被 OHOS 沙盒拒绝, try-compile 失败 (E346), 非编译器本身问题 | 主包 build()/package() 与 test_package build() 统一 cmake.generator="Ninja" (duckdb/1.2.0 先例), Ninja 直接 exec 编译器绕过 /bin/sh |
| 6 | 同一指纹第 2 次失败: Ninja 已进预检 (报错行号 60→64 证实新代码已跑) 但 project() 处 compiler broken 依旧, 兼报 [readonly_tmp] | 仅换 generator 是按错误码相似误套 E346, 真机证据不足; 同机 backward-cpp 默认 Makefiles 可构建, 说明 generator 非 differentiator, 真机 /tmp 只读下编译器临时文件可能回退到 /tmp 而 plain os.environ 又可被 toolchain env 过滤 (audtty/hunspell/cataract 先例) | 新策略: ①generate() 复用 HMBS 注入的 TMPDIR/TMP/TEMP 链 (缺失回退 build_folder/tmp) 并经 Environment().save_script 显式透传进 conanbuild 环境, build() 内再 setdefault 双保险, 主包与 test_package 同步; ②build() 包裹 cmake.configure(), 失败时转储 CMakeError.log/CMakeOutput.log 末 80 行再抛 (complexity _dump_test_logs 先例), 使下次预检自带真实 try-compile 错误; ③修正 _run_upstream_tests 的 ctest cwd: 自动发现含 CTestTestfile.txt 的 preset 二进制目录 |
| 10 | source()直连github.com两次ConnectTimeout(30s,各等5s重试)后ConanException,失败行conanfile.py line 46 get();属守则源码包下载超时例外,须加镜像回退 | 真机到github.com建连超时,预检直接conan create不经过CI的Mirror fallback改写,故配方内须自带有序列表 | 本轮仅改conandata.yml:url有序列表gh-proxy镜像在前、官方原URL最后回退(ci/conan/build_and_test.sh的GitHub映射),sha256不变;编译侧改动(上一轮WORKS断言等)保持不动 |
| 9 | Same fingerprint 5th failure: Linux SYSTEM_NAME active (error line 124->125 proves new code ran) but C/CXX compiler identification unknown + broken identical at CMakeLists project() | Prior levers all targeted try-compile sub-steps (generator/shell/tmpdir/link/system-name) yet the works-check gate itself never passes on this worker; E191 STATIC_LIBRARY only skips link stage and already failed, so gate failure is not link-specific | New route (extra-cmake-modules/6.28.0 merged precedent for OHOS clang detection failure): set CMAKE_C/CXX_COMPILER_WORKS=1 cache to skip project() works try-compile gate; real compilation still runs fully in build() and true breakage fails loudly there; keep Ninja/TMPDIR/Linux-name/log-dump; test_package configure mirrors WORKS vars |
| 8 | Same fingerprint 4th failure: Ninja+TMPDIR+STATIC_LIBRARY all ran (line numbers shifted each round) but project() compiler broken identical; CMakeError dump never visible in focused summary, ettercap libxml2 link hypothesis has no log evidence for oclgrind | Direct log evidence this round: System is unknown to cmake, create Platform/HarmonyOS + cmake 4.4.3, untouched by all 3 prior cycles | New route: OHOS force CMAKE_SYSTEM_NAME=Linux + PROCESSOR=aarch64 in main generate() and test_package configure (zxc/0.9.1, dcmtk/3.6.7, c3c/0.8.1 merged precedents); drop unproven STATIC_LIBRARY mask so real try-compile link runs; keep Ninja (still bypasses /bin/sh in build) + TMPDIR透传 (readonly_tmp diagnostic) + log dump; revert conandata gh-proxy mirror to single official URL (PF7/R39 blacklist, CI build_and_test.sh auto-adds gh-proxy fallback) |
| 11 | project() 处 C/CXX compiler broken 同指纹第 6 次失败, 兼报 [readonly_tmp]; 上一轮自研的 150 行 linker-probe 在预检中 ambient 通过但 cmake 依旧失败, 无 lld 日志证据, 属按错误码误套经验 | 聚焦摘要被省略日志截断, 真实 try-compile 错误不可见; 自研 probe 的 bare-cc 成功与 CMake try-compile (带 sysroot/target flags) 不等价, 且 c-ares/1.34.5 (E266) 与 zstd/1.5.6 已有同症状已合入解法: OHOS SDK lld 动态链接 libxml2.so.16, worker 沙箱搜不到导致 lld 起不来 | 本轮改动: ①主包/test_package 同步删自研 probe, 改用 E266 最小形式: generate() 经同一 Environment 脚本前置已存在的 SDK llvm/lib (固定路径+版本 glob, 与 c-ares 同路径), build() 内再经 os.environ 前置双保险 (zstd 形式); ②保留 Ninja (E346) 与 TMPDIR 透传 (readonly_tmp); ③configure 失败时把 CMakeError.log 尾部嵌入 ConanException 文本 (info 输出常被摘要省略, 异常文本必现), 使下轮自带根因; 不加 SYSTEM_NAME 覆写/COMPILER_WORKS/STATIC_LIBRARY (多轮已证伪或违反 fail-closed) |
| 12 | project() C/CXX compiler broken same fingerprint 7th failure, CMakeError.log tail "(empty)", info-level dump invisible in focused summary | fixed-path-only llvm/lib lookup silently misses on SDK drift + info-level dump filtered as irrelevant + narrow log search misses CMake4 preset layout, leaving next round with zero evidence | this round: 1) _ohos_sdk_llvm_lib toolchain-derived first (clang realpath walk, ls-hpack minimal) + fixed + glob fallback, warning-level decision log, main+test_package sync; 2) _dump broadened (*.log under CMakeFiles, 8 files x100 lines, error level) + non-empty fallback (build-tree listing embedded into exception); 3) keep Ninja/TMPDIR/E266, no SYSTEM_NAME/COMPILER_WORKS/STATIC_LIBRARY |
| 13 | same fingerprint 8th failure: new warning proves llvm/lib lookup finds nothing on worker + tree proves CMake4.4 logs to CMakeConfigureLog.yaml (no CMakeError.log, empty CompilerId tmp) | fixed-path/toolchain-derived llvm/lib assumption falsified by machine evidence; prior dump searched only legacy log names so tail stayed empty | this round (different strategy): 1) _dump rewritten for CMake4: prioritize CMakeConfigureLog.yaml failed-event filtering + CMakeCache, error level, embed into exception; 2) missing llvm/lib now emits SDK base listing (which clang/realpath + hnp/sdk.org dirs) at warning level instead of silent skip; 3) no compiler-bypass, keep Ninja/TMPDIR |
| 7 | 同一指纹第 3 次失败: TMPDIR 透传已进预检 (报错行号 64→117) 但 project() 处 C/CXX compiler broken 依旧, 转储日志在聚焦摘要中不可见 | 站内无 oclgrind Issue/PR 可取原始日志 (300 条 Issue + 200 条 PR 检索无命中); 转向合入先例的精确根因: ettercap/0.8.4.1 配方写明"真机 lld 加载不出 libxml2.so.16, try-compile 链接失败于 project() 阶段", 与本错 C/CXX 双编译器同报、行号、阶段完全吻合, 同机他包正常系 worker 间宿主库差异 | 新策略: ①主包 generate() 在 OHOS 下置 tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"]="STATIC_LIBRARY", 跳过 try-compile 链接步 (ettercap/alfa/lapack/boost 先例); ②test_package build() 经 cmake.configure(variables={...}) 同样跳过 (cryptokit/1.21.1 先例); 保留 Ninja (构建阶段仍需绕过 /bin/sh)、TMPDIR 透传与日志转储。副作用: 上游 check_library_exists 测不出 readline 时仅警告并关历史记录 (HAVE_READLINE=0), 不致命, 真实链接仍走正常路径 |
| 14 | 第 5 策略周期: 前 4 轮编译器路径/TMPDIR/lld 路线已证伪——本轮预检 configure 已越过 project() 探针 (编译器可达), 倒在 CMakeLists.txt:52 find_package(LLVM REQUIRED CONFIG) 找不到包配置。上游硬要求 LLVM>=18 + Clang 头/库/opencl-c.h/clang 二进制; 真机 SDK clang 为 15.0.4 (<18), 仓库 llvm/20.1.0 与 llvm/22.1.0 均以 LLVM_ENABLE_PROJECTS="" 构建 (无 clang 前端), 仓库 clang/20.1.8 与 clang/22.1.8 均为 built 未发布 (R36/PF4 下不可 requires, 否则触发数小时源码构建)。继续调编译器路径属同根因假设, 本周期禁用 | 缺的不是编译器可达性而是 LLVM>=18 开发包, 属"换网络正常的机器也解决不了"的 env_unsupported 类 (SKILL 现象→status 对照表: 工具链版本不符) | 本轮改动 (与前 4 轮不同路线): ①保留已生效的编译器回退/Ninja/TMPDIR (不动已证实有效的部分); ②主包 validate() 新增 _validate_llvm_for_ohos: 在 OHOS 下先探测 LLVMConfig.cmake (LLVM_DIR/CLANG_ROOT/OHOS_SDK_LLVM_ROOT + /usr/lib/llvm-*/lib/cmake/llvm 等) 与 llvm-config --version, 仅当存在 >=18 证据或无版本后缀的 config 文件时才放行让 CMake 做权威VERSION检查, 否则直接 raise ConanInvalidConfiguration 并附机器证据 (llvm-config/clang 双探针版本 + 仓库状态说明), 把晦涩的 CMake 报错提前为可行动的 fail-fast; ③刻意不加 requires/tool_requires 指向未发布的 llvm/clang (R36/PF4, 且会触发数小时 clang 源码构建超预检超时)。未跳过任何测试, 未加编译器旁路 |
| 15 | 同指纹第 2 次修复: 上一轮 fail-fast 按设计生效——预检以退出码 6 在 validate 阶段失败, 机器证据 llvm-config probe='15.0.4'、clang probe='clang version 15.0.4 (...llvm15_release...)' 与诊断完全吻合, 证实缺 LLVM>=18 而非编译器可达性问题。按防重复要求不得原样重复上一修改, 本轮换用不同策略: 不再动失败判定逻辑, 改为铺设免改配方的解堵路径 | 即使判定正确, 配方仍缺一条"LLVM>=18 出现后自动接通"的通道; 否则未来 clang>=18 工具链包发布或真机出现系统 LLVM>=18 时仍需再改一轮配方 | 本轮改动: ①validate() 探测根新增 user.oclgrind:llvm_dir conf (与 LLVM_DIR/CLANG_ROOT/OHOS_SDK_LLVM_ROOT 同权), conf 指向的 >=18 前缀可直接放行; ②generate() 新增 LLVM_DIR/CLANG_ROOT 透传 (conf 优先、env 回退), 经 tc.cache_variables 交给 find_package, 无提供时不做任何事 (validate 已提前失败); ③报错文本把解堵方式写死为 "LLVM_DIR/CLANG_ROOT env 或 -c user.oclgrind:llvm_dir=<prefix>"。仍未加 requires/tool_requires (R36/PF4)、未降上游版本要求、未跳过测试 |
| 16 | 本轮聚焦: fail-fast 已按设计生效 (退出码 6, 机器证据 15.0.4 与诊断吻合, 缺 LLVM>=18 属 env_unsupported 非配方 bug) + 兼报 [readonly_tmp] (preflight.sh 自身 /tmp 只读)。再调判定逻辑属重复旧路 | 上游 /tmp 硬编码审计 (v26.03.1 实测): 全源码仅 src/core/Program.cpp 的 OCLGRIND_DUMP_SPIR opt-in 分支写 /tmp (CL/IR/BC_DUMP_NAME 三个宏为死代码), tests/ 无 /tmp, 默认 ctest 路径不触 /tmp; 另 source() 无重试, 历史上曾遇 github 建连超时 | 本轮改动 (与前 15 轮不同路线, 判定逻辑不动): ①新增 patches/0001-tmpdir-env.patch, dump 临时根改为 TMPDIR→TMP→TEMP→/tmp 链 (仅换根、不删测试、无平台宏; clang/20.1.8 的 gtest TMPDIR 补丁先例; 已在解压源码上 git apply 零偏移验证); ②source() 加 5 次重试并告警 (PF7/R39 合规: 仍单官方 URL, 不加黑名单镜像, 与已回退的 mirror-list 不同路); ③LLVM fail-fast 与 requires 策略保持不动 |
| 17 | 同指纹第 3 次修复: 前两轮的 fail-fast/conf 透传与 tmpdir 补丁均未改变退出码 6 (validate 在 source/build 之前拦截, 补丁与重试从未被执行); 且上轮发现调用已合入但辅助方法因中断缺失, 本轮先补全 | 上游 CMakeLists 实测: 除 find_package(LLVM)+VERSION>=18 外, 还硬需 clang/CodeGen/CodeGenAction.h 头、clangFrontend (或 clang-cpp) 库、lib/clang/<major>/include/opencl-c.h、clang 二进制——缺任一即 FATAL, 故可用前缀必须四者齐备; 仓库 clang/20.1.8 仍为 built 未发布, requires 路线仍被 R36/PF4 封死 | 本轮改动 (新路线, 无 requires、无网络、无跳过测试): ①补全 _discover_usable_llvm_prefix 及三个辅助方法 (llvm-config --prefix 派生 + conan 本地缓存只读扫描, 版本取自 LLVMConfigVersion.cmake, 四者齐备才放行); ②generate() 在 conf/env 缺席时透传发现的前缀 (LLVM_DIR+CLANG_ROOT); ③fail-fast 文案注明已做本地发现。本地以桩 conan 模块验证: 完整前缀发现可用、llvm-only 前缀被正确拒绝 (缺 4 项 clang 制品) |
| 18 | 第 6 策略周期: 前三轮( fail-fast/conf 透传/tmpdir 补丁/本地缓存发现)连续以退出码 6 卡在 validate, 机器证据始终为 llvm-config/clang 双探针 15.0.4, 证明真机根本没有 LLVM>=18+Clang 前缀; 上轮本地桩验证仅证伪了发现逻辑本身, 非真机证据, 按防重复要求不得再调发现逻辑 | 缺的不是发现手段而是 LLVM>=18 实物 (SDK clang 15.0.4<18; 仓库 llvm/20.1.0 与 llvm/22.1.0 以 LLVM_ENABLE_PROJECTS="" 构建无 clang 前端; 仓库 clang/20.1.8 与 clang/22.1.8 为 built 未发布, R36/PF4 下不可 requires, 否则触发数小时源码构建); 另本轮 [readonly_tmp] 来自 preflight.sh[306] 自身 mktemp 写只读 /tmp, 属真机基础设施故障, 配方侧 /tmp 早已加固 (TMPDIR 链 + 0001-tmpdir-env.patch), 配方改不动 preflight.sh | 本轮做减法 (与前三轮加法不同路): ①删 _discover_usable_llvm_prefix 及三辅助方法与 validate/generate 两处调用, validate 回归 conf/env 标准探测 (user.oclgrind:llvm_dir conf + LLVM_DIR/CLANG_ROOT/OHOS_SDK_LLVM_ROOT env + 标准根 + llvm-config 版本探针), fail-fast 与解堵文案保留; ②generate 只透传 conf/env, 不再二次扫描缓存; ③readonly_tmp 按守则判为环境故障上报, 不再动配方 /tmp; 未加 requires、未降版本门槛、未跳过测试 |
| 19 | 同一指纹第 2 次修复: 上轮做减法已部署 (本轮日志出现精简后文案即证据) 但退出码 6 依旧，双探针仍为 15.0.4；按防重复要求不得再改 validate 文案，必须换路线。本轮改挖仓库先例：ccls/0.20250306.8 跟踪中配方以 requires("clang/22.1.8") 消费仓库内 clang，其 notes 明确 "ohpcd 制品仓已发布" (libclang-cpp.so + libLLVM.so + 头 + LLVM/Clang CMake config + lib/clang/22 资源目录)，证伪了我方 notes 长 Ramp 假设 "clang 未发布、无 R36 合规 requires"；spirv-llvm-translator/20.1.0 以 requires("llvm/20.1.0") 为第二先例 | 缺的一直是实物而非探测手段：SDK clang 15.0.4<18，llvm/20.1.0 系 LLVM_ENABLE_PROJECTS="" 无 clang 前端故 llvm-only 不够格，而 clang/22.1.8 包内 LLVM 22 + Clang 四件套齐备且上游 CMakeLists 显式支持 >=22 (VERSION_GREATER_EQUAL 22.0 CLANG_LIBS 分支，含 dylib 回退到 clang-cpp) | 本轮改动 (与前六轮"找 LLVM"均不同路，改为正式依赖)：①requirements 新增 requires("clang/22.1.8") (与 ccls 同版本)；②删除 _validate_llvm_for_ohos fail-fast 门禁，LLVM 由依赖保证提供；③generate 改走 ccls 布线：conf/env 显式覆盖优先，否则以 clang 包目录推导 LLVM_DIR (<pkg>/lib/cmake/llvm) 与 CLANG_ROOT (<pkg>) 并设 CMAKE_PREFIX_PATH 指向包内自带 LLVMConfig/ClangConfig (ccls 教训：不让生成 config 遮蔽)；其余 Ninja/TMPDIR/lld/编译器回退/tmpdir 补丁/97 用例 ctest 均不动 |

| 20 | ctest 97 用例中 92 失败、5 通过；通过的 5 个恰为 LLVM>=22 的 WILL_FAIL/XFAIL 用例 (interactive 2 + memcheck 3)，即实际上 100% 用例执行失败，属系统性运行时缺库而非单个用例回归；构建链接成功说明 -L 查找正常，失败必在测试子进程启动阶段 | oclgrind 链接 clang/22.1.8 的共享库 libclang-cpp.so/libLLVM.so (+readline 共享库)，而该 clang 配方无 runenv_info，plain cpp_info libdirs 不会自动进 LD_LIBRARY_PATH，ctest 经 raw Popen 启动的子进程装载器找不到共享库而全部启动失败；XFAIL 反转后呈现为 92 失败/5 通过 | 本轮改动 (新路线，不碰测试口径)：①新增 _host_dep_libdirs (clang/readline 的 lib/lib64，现存才收)；②generate() 经同一 Environment 脚本把 dep libdir 前置进 LD_LIBRARY_PATH；③_prepare_ohos_lld_env 经 os.environ 同步前置 (SDK llvm/lib 缺失时仍执行)；④_run_upstream_tests 在 Popen 前再做一次兜底并告警打印 LD_LIBRARY_PATH。未跳过任何测试、未改断言 |
| 21 | 同指纹第 3 次修复：上一轮 dep libdir 前置已部署 (新 WARN 行即证据，LD_LIBRARY_PATH 含 clang/readline 包 lib) 但结果原样 92 失败/5 通过，缺共享库假设被机器证据证伪；按防重复要求换路线。本轮不做运行时假设，只做诊断前置 | 聚焦摘要恒截中段，ctest 真实失败文本从未到达下一轮，连续两轮在无输出下猜测根因 | 本轮改动 (纯诊断，不碰测试口径)：①新增 _ctest_failure_excerpt (首个 ***Failed 块 + 尾部汇总，上限 60 行，本地单测通过)；②新增 _probe_test_runtime (PCH 目录清单 + oclgrind-kernel --version 探针，区分装载失败与内核编译失败)；③失败时 error 级输出两者并嵌入 ConanException 文本 (异常文本必现通道)；探针只读、异常兜底，永不破坏流程 |
| 22 | 本轮诊断前置生效：首次拿到真实失败文本——每个用例报 Error relocating oclgrind-kernel: oclgrind::Program/Kernel/Memory 等全部自有符号 symbol not found；上一轮缺 clang 共享库假设被证伪 (LD_LIBRARY_PATH 已含 clang/readline 但失败指纹变为全量自有符号缺失)，按防重复要求换路线 | 构建链接成功但运行时全部 oclgrind 自有符号解析失败，典型为 DT_NEEDED 的同构建树 liboclgrind.so 找不到 (OHOS 构建 RPATH 不解析兄弟库；musl 在缺库时对该库全部符号报 relocating 失败)；此前只前置了 clang/readline 包目录，从未前置刚构建出的 lib 目录 | 本轮改动 (新路线，不碰测试口径)：①新增 _built_lib_dirs (test_dir+build_folder+含 liboclgrind*.so 的目录，上限 12，只读 walk)；②_run_upstream_tests 在 Popen 前把 built libdir 前置进 LD_LIBRARY_PATH 并 WARN 打印 (与 dep libdir 同通道，ctest 子进程继承)；③探针沿用同一环境，无需改动。未跳过任何测试、未改断言 |
| 23 | 上轮 built-libdir 生效：92 失败→8 失败 (89/97 通过)，剩余 7 个 launcher 类 (app 2+rt 5) 同报 [Oclgrind] Unable to resolve path to Oclgrind installation，另有 1 个 kernel 类 atomic_intergroup_race；与上轮 LD_LIBRARY_PATH 路线不同指纹，按防重复要求换路线 | oclgrind launcher (src/runtime/oclgrind.cpp getLibDirPath) 先 readlink /proc/self/exe 再 realpath 规范化，realpath 失败即 exit(1)；真机沙箱 /proc 受限 (预检头即报 can't open /proc/*/cmdline)，readlink 成功但 realpath 失败导致全部 launcher 用例启动即退出；kernel 类直调 oclgrind-kernel 不经 launcher，故 89 个通过 | 本轮改动 (新路线，不碰测试口径)：①新增 patches/0002-oclgrind-exe-realpath-fallback.patch，realpath 失败时回退用未规范化 exepath，只取其所在目录，不再退出；②conandata.yml+manifest.yaml 登记该补丁；③不标记 WILL_FAIL、不跳过任何测试，atomic_intergroup_race 留待下轮首失败摘录判定 |
| 24 | 本轮聚焦：上游 ctest 已 97/97 通过，倒在 test_package 链接：ld.lld 报 undefined symbol clGetPlatformIDs/clGetPlatformInfo/clGetDeviceIDs (test_oclgrind.c.obj)，conan create 退出码 1；与之前 92 失败/8 失败的运行时指纹不同，按防重复要求换路线 | OpenCL 入口符号在自带 liboclgrind-rt (SONAME libOpenCL.so) 中，opencl-headers 仅提供头文件；test_package 原只链 oclgrind::oclgrind + opencl-headers::opencl-headers，OHOS 下该接口未带上 rt 实现库，链接期即缺符号（非运行时缺库） | 本轮改动 (只加链接不断言不跳过)：①test_package/CMakeLists.txt 用 OCLGRIND_PACKAGE_FOLDER 显式 find_library(oclgrind-rt/OpenCL，包内 lib/lib64 优先、无包路径时回退默认搜索) 并追加 target_link_libraries；②test_package/conanfile.py build() 把 self.dependencies["oclgrind"].package_folder 透传为 OCLGRIND_PACKAGE_FOLDER；③主包 package_info 不动 |
| 25 | 本轮聚焦: 真机 compile 阶段 Signal 9 (SIGKILL, 空 stdout/stderr, 上游测试 0/0/0), 与之前 97/97 通过及 test_package 链接指纹均不同, 按防重复要求换路线 | Signal 9 在无编译错误输出下恒为 OOM killer: oclgrind 每个 TU 均含重型 LLVM/Clang 头, 默认 Ninja 按 nproc 并行, 峰值内存撑爆受限 worker; HMBS 虽注入 tools.build:jobs=1, 配方内未显式限并发, conf 缺失即回退并行 | 本轮改动 (只限并发不碰测试口径): ①主包 build() 改为 cmake.build(cli_args=["-j1"]) (wxWidgets/3.2.6 已合入先例, OHOS 并行约束); ②test_package build() 同步 -j1; 不降优化等级、不跳过任何测试 |
## 源码修改

- patches/0001-tmpdir-env.patch: SPIR dump 临时目录优先取 TMPDIR/TMP/TEMP，回退 /tmp；仅换临时根，不跳过测试，无平台宏。

## 依赖版本

- readline/8.3 (已发布, 交互调试器历史记录支持; 缺失时上游仅警告, 不致命)
- 其余构建依赖 (LLVM >= 18 + Clang 头/库/二进制/opencl-c.h, Python) 由真机环境提供, 未写入 conan 依赖

## 验证结果

```bash
# 待 HMBS 真机预检 (conan create) 返回后如实回填
# 预期: ctest 97 用例 + test_package 2 用例
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/oclgrind | OpenCL 应用启动器 (LD_PRELOAD liboclgrind-rt) |
| bin/oclgrind-kernel | 内核仿真器 (ctest 驱动) |
| lib/liboclgrind.so | 核心模拟器库 |
| lib/liboclgrind-rt.so (SONAME libOpenCL.so) | OpenCL 运行时前端 |
| include/oclgrind/ | 核心头文件 + opencl-c.h 及 PCH |

## 注意事项

- oclgrind 运行缓慢 (解释执行 LLVM IR + 逐访问界检查), 建议小规模问题验证。
- oclgrind-kernel 与 ctest 依赖 OCLGRIND_PCH_DIR 指向构建产物 include/oclgrind, 配方内已按上游 CTest 属性设置。
- 本机为 Windows, 不运行 conan; 一切数字以真机预检日志为准, 不估算。
