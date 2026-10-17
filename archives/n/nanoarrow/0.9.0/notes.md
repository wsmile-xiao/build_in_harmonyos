# nanoarrow 0.9.0 适配笔记

## 编译环境

- 构建系统: cmake（核心库 `nanoarrow_static`/`nanoarrow_shared` + 安装配置 `nanoarrow-config.cmake`）
- 编译日期: 2026-09-10
- 编译器: clang/clang++
- 状态: built（首轮工作树，真机预检待 HMBS 后台执行）

## 上游核验

- 官方仓库: https://github.com/apache/arrow-nanoarrow
- 正式 tag: apache-arrow-nanoarrow-0.9.0
- tag 解引用 commit: 9fad80292360d0f3978264c11ba865ccc94020d8
- 官方 tag tarball sha256: 22c3edeaa5cb384c6da091f32a4e1c937779f2d62f84d646028de658b03d4385（已下载核验，大小 1121343 字节）
- 许可: Apache-2.0（LICENSE.txt + NOTICE.txt，随包安装到 licenses/）
- 产品形态: `nanoarrow::nanoarrow`（静态默认）；IPC/DEVICE 扩展默认关闭
- 构建选项: NANOARROW_BUILD_TESTS=ON、NANOARROW_BUILD_TESTS_WITH_ARROW=OFF（不依赖 Arrow C++）、IPC/DEVICE/APPS/BENCHMARKS 全部 OFF
- 上游测试: 12 个 gtest 二进制（utils/buffer/array/schema/array_stream/testing/c_data_integration/hpp 系列 5 个），随源码 vendored googletest，无需外网下载

## 编译步骤

核心库零外部依赖，标准 CMake 流程：

```bash
cmake -S . -B build -DBUILD_SHARED_LIBS=OFF -DNANOARROW_INSTALL_SHARED=OFF \
  -DNANOARROW_IPC=OFF -DNANOARROW_DEVICE=OFF -DNANOARROW_BUILD_TESTS=ON \
  -DNANOARROW_BUILD_TESTS_WITH_ARROW=OFF -DNANOARROW_BUILD_APPS=OFF \
  -DNANOARROW_BUILD_BENCHMARKS=OFF -DNANOARROW_BUILD_INTEGRATION_TESTS=OFF
cmake --build build
ctest --output-on-failure --test-dir build
```

配方内 build() 先 `cmake.configure()` + `cmake.build()`，再 `self.run("ctest --output-on-failure")` 真实执行上游套件，
随后 `_emit_hmbs_upstream_marker()` 重跑 ctest 解析汇总行输出 `HMBS_UPSTREAM_TEST_RESULT` 并持久化
`build_folder/hmbs_upstream.json`，`package()` 拷贝至 `res/hmbs_upstream.json` 供 test_package 每轮复发（覆盖 Conan 缓存命中轮次）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 tag 命名非 `v0.9.0` 而是 `apache-arrow-nanoarrow-0.9.0` | Arrow 单仓多包发布规范，nanoarrow 独立 tag 前缀 | conandata URL 采用完整 tag 归档路径，已按 commit 核验 |
| 2 | `cmake.test()` 日志无 ctest 命令痕迹，L1c 证据不足 | `cmake.test()` 驱动 CMake 的 test 目标，不转发 `--output-on-failure` | 改用 `self.run("ctest --output-on-failure", cwd=build_folder)`，日志保留 `RUN: ctest` |
| 3 | 缓存命中轮次 build() 不执行，上游证据标记消失 | Conan 缓存命中跳过 build() | 证据持久化到 `package/res/hmbs_upstream.json`，test_package 每轮复发 |
| 4 | test.c 初稿 `ArrowSchemaViewInit` 参数个数错误 | 该接口需 `(view, schema, error)` 三参 | 补 `struct ArrowSchemaView view` 并按三参调用 |
| 5 | 真机预检 compile 失败：CMake compiler check 报错 + `preflight.sh: can't create temporary file /tmp/*.tmp: Read-only file system`（HMBS readonly_tmp 诊断） | OHOS 真机 /tmp 只读挂载，clang 中间文件默认落 /tmp（$TMPDIR 未指向可写目录），CMake 编译器检查失败 | 主配方与 test_package 新增 `_use_writable_tmpdir()`：优先复用 HMBS 注入的 `HMBS_TMPDIR`/`TMPDIR`（可写性探针验证），兜底 `build_folder/tmp`；`build()` 首行调用并导出 `TMPDIR/TMP/TEMP`，test_package 的 `test()` 同样前置调用 |
| 6 | 同一 readonly_tmp 在上一轮修复后复现：CMake `project()` 编译器检查仍报 `/data/service/hnp/bin/clang` 失败 | 上轮仅在 `build()` 内改 `os.environ`，Conan 的 CMake 编译器探测经 `conanbuild.sh` 取环境，`os.environ` 未透传；且优先级误用不存在的 `HMBS_TMPDIR` | 本轮改用 enigma 式 `generate()` 透传：`Environment().define(TMPDIR/TMP/TEMP).save_script()` 主包 `nanoarrow_tmpdir` + 测包 `nanoarrow_test_tmpdir`，优先级纠正为 `TMPDIR/TMP/TEMP` + `build_folder/tmp` 兜底并保留 `build()` 内 `os.environ` 双保险 |
| 7 | 上述 buildenv 透传后仍在 `cmake.configure()` 复现：`System is unknown to cmake` + C/CXX 编译器双双 broken（两次 TMPDIR 策略均无效，证伪 TMPDIR 为主因） | CMake 无 `Platform/HarmonyOS.cmake`，`CMAKE_SYSTEM_NAME=HarmonyOS` 下编译器检查失败；真机 `preflight.sh[306]` 的 `/tmp` 报错来自 harness 自身而非配方 | 本轮改用 zxc/byte-lite/function2 已验证策略：`generate()` 内 `os==OHOS` 时 `tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"` + `PROCESSOR=aarch64`；测包同步由 `generators` 属性改显式 `CMakeToolchain`（byte-lite 测包先例）以便同覆盖；TMPDIR 透传保留 |
| 8 | Linux 伪装后仍复现 `compiler identification is unknown` + clang 路径报错（三轮 TMPDIR/Linux 策略连续证伪） | 上轮 `tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"`（E092 旧策略）与真机 CMake 4.4.3 失配：新版 CMake 自带 `Platform/OHOS.cmake`（yaml-cpp 0.9.0 已验证），Conan 默认 `HarmonyOS` 无模块才是病因；Linux 伪装还被 DRAFT-nng 明令禁止；且上轮 dropped `HMBS_TMPDIR`（scooter/backuppc-rsync/boost 日志实证该变量存在）导致优先级回退 | 本轮改走 yaml-cpp 路线：主包+测包 `generate()` 改 `tc.blocks["generic_system"].values["cmake_system_name"]="OHOS"` + `processor=aarch64`，删 `cache_variables` Linux 覆盖；TMPDIR 优先级恢复 `HMBS_TMPDIR>TMPDIR/TMP/TEMP>build_folder/tmp`（双包 `generate()`+`build()/test()` 双保险保留） |
| 9 | OHOS 平台块修正后仍复现同一指纹：`C/CXX compiler identification is unknown` + `/data/service/hnp/bin/clang` 配置中断（与前次逐字相同，证伪 SYSTEM_NAME 为主因） | 前四轮均聚焦 TMPDIR/SYSTEM_NAME；截断日志隐藏了编译器自检真实 stderr。跨库核查发现 julius/c-ares/E266 同 symptom：OHOS SDK 的 lld 动态链接 `llvm/lib/libxml2.so.16`，worker 加载器按 RUNPATH 命中失败导致链接器无法启动，CMake 即报编译器 broken；另真机 CMake 4.4.3 对老 `cmake_minimum_required` 需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（julius/milkytracker 先例），本配方从未设置 | 本轮换全新路线（不动 SYSTEM_NAME）：双包新增 `_sdk_llvm_lib_candidates/_inject_sdk_llvm_lib`（`clang -print-resource-dir` 动态推导 + glob 兜底，仅含 libxml2 时注入，R33 无硬编码），`build()` 在 `cmake.configure()` 前注入 `LD_LIBRARY_PATH`，`generate()` 经 `Environment.prepend_path` 持久化进 conanbuild.sh；双包 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"` |
| 10 | LD_LIBRARY_PATH + POLICY_VERSION_MINIMUM 组合后仍逐字复现同一指纹（`build()` line 121 `cmake.configure()` 中断，前次修改证伪 lld 缺库为主因） | 前五轮全部围绕 Conan CMakeToolchain 打补丁（TMPDIR 两轮 + Linux/OHOS 平台名两轮 + lld/策略一轮），指纹零变化，说明 conan_toolchain 在 os=OHOS 下的映射本身即病灶（xxhash/zstd 注记 ML-0035：映射成 cmake 不认的值）；截断日志始终隐藏真实 stderr，盲调 conan_toolchain 已无收敛迹象 | 本轮改走 xxhash 0.8.3/zstd 1.5.7.1 已验证路线：双包删除 CMakeToolchain，`generate()` 仅保留 TMPDIR + LD_LIBRARY_PATH 的 buildenv 脚本；`build()` 自发现 NDK `ohos.toolchain.cmake`（user_toolchain/OHOS_NDK_HOME/SDK glob）后裸 `cmake -B build-ohos -S source -DCMAKE_TOOLCHAIN_FILE=... -DOHOS_ARCH=arm64-v8a` 配置构建安装，上游 ctest 与证据标记指向 build-ohos；测包同法直传 `-Dnanoarrow_DIR`；`package()` 加 .so 自签（静态默认时 no-op） |
| 11 | 裸 cmake 路线首跑即报 `Invalid configuration: Cannot find ohos.toolchain.cmake`（build() 未进 configure，与前五轮 compiler unknown 指纹不同，证伪“NDK 必存在”假设） | 上轮硬依赖 NDK 文件：`_ohos_toolchain()` 仅查 user_toolchain + OHOS_NDK_HOME + 单一 glob `/data/service/hnp/ohos-sdk.org/*/ohos/...`；而 CI profile（ci/conan/profiles/ohos-aarch64）根本不设 user_toolchain/OHOS_NDK_HOME，仅给 compiler_executables + PATH/LD_LIBRARY_PATH，预检同源故同样缺 NDK，glob 在 SDK 版本漂移/布局变化时返回空即硬抛错 | 本轮换混合路线（与前六轮不同）：回切 yaml-cpp 0.9.0 已验证的纯 CMakeToolchain + `generic_system OHOS/aarch64`（CMake 4.x 自带 Platform/OHOS.cmake，无需 NDK 文件；profile clang 直驱），保留 POLICY_VERSION_MINIMUM=3.5 + TMPDIR/LD_LIBRARY_PATH 双保险 + ctest 证据链；NDK 发现降级为诊断日志不再抛错；签名工具改编译器旁→/data/service/hnp/bin→PATH 三级发现 |
| 12 | 回切纯 CMakeToolchain 后复现 compiler identification unknown（与前次同指纹，证伪“generic_system 即足够”） | 上轮仅诊断 NDK 是否存在但找到也不用，仍用无 sysroot/target 的 profile clang 直驱；且 LD 修复仅取首个含 libxml2 的 llvm/lib（版本漂移即静默失效），CMakeError 日志仅记 present 不贴内容致盲调 | 本轮改混合落地路线：generate/build 双侧穷举 NDK（env 三布局+编译器实路径派生+宽 glob+60s find 兜底，找到即走裸 cmake+NDK 真 sysroot，否则才走 Conan 链）；LD 改为全部现存 llvm/lib 无条件前置；build 前打印 clang --version/resource-dir 与 TMPDIR/LD，失败必贴 CMakeError/Output 尾 6000 字 |
| 14 | 真机 compile 阶段 /bin/sh: Out of memory（上游测试 0/0/0） | 配方在低内存真机上同时做三件重事：裸 NDK 路径 cmake --build 未限并行（忽略 hmbs 注入的 tools.build:jobs=1，并行链接 12 个 gtest 二进制易 OOM）；build() 先 self.run(ctest) 又在 _emit 内 subprocess 重跑 ctest（2x fork+内存/时间）；generate/build 双侧 find 递归扫 /storage /data /opt（多个 find 子进程+大 stdout 缓冲） | 本轮只做低内存瘦身不改测试口径：裸构建加 --parallel 1、双路径置 CMAKE_BUILD_PARALLEL_LEVEL=1；ctest 合并为 _run_ctest_and_emit 单次执行并解析标记；删除 find 递归兜底（编译器/NDK 只留 profile+which+绝对路径+env+glob 廉价检查，复用 hmbs 已注入 PATH/jobs）；保留 ctest 证据链与 test_package 复发 |
| 13 | 混合路线后新证据：profile 的 `/data/service/hnp/bin/clang` 在预检机根本不存在（Errno 2，NDK 同样未找到，日志报 log absent） | 前三轮均信任 profile compiler_executables 硬编码路径；预检机工具链在 /storage 下而 CI 在 /data 下，路径漂移致 CMake 拿死路径必报 unknown；且 dump 只看 build_folder 根而 cmake_layout 实际在 build/Release，故 log absent | 本轮换编译器发现路线：generate 双包新增 _discover_ohos_compilers（profile 仅当文件存在且 --version 通过才用，否则 PATH/绝对路径/SDK llvm-find 穷举并经 --version 验证，命中则 pin CMAKE_C/CXX_COMPILER）；NDK 搜索补 /storage 根；dump 改搜 build/build-Release/build-ohos 四目录 |

| 15 | 真机 upstream_test 失败：ctest 明明跑了 258 个用例（Start 258、Skipped 行可见）却上报 `discovered:0/executed:0`，`_run_ctest_and_emit` 直接 RuntimeError；另有 1 个 `ThreadSafeClone (Skipped)` 常驻 | 旧解析只认 `% tests passed` 汇总行，汇总缺失（OOM 提前杀死/措辞漂移/目录错位）即报 0/0/0；且 IPC=OFF 时上游默认 C99 导致 `ArrowSharedBufferIsThreadSafe()==0`，3 个线程克隆测试走 `GTEST_SKIP`；另 `bdir` 未校验 `CTestTestfile.cmake`，`ctest` 裸命令依赖 PATH | 主配方 `generate()` 强制 `CMAKE_C_STANDARD=11/CXX_STANDARD=14`（NDK 裸路径同加），使原子检测通过、跳过变实跑；新增 `_resolve_ctest_dir/_resolve_ctest_bin`（按 `CTestTestfile.cmake` 选目录、按 `HMBS_CMAKE` 旁/which 定 ctest 绝对路径），ctest 改 `--parallel 1` 串行 + 透传可写 TMPDIR + `CTEST_PARALLEL_LEVEL=1`；解析加 `Skipped/Not Run` 计数与无汇总时按 `... Passed/Failed/Skipped` + `Test #N/Start N` 回退计数，`executed=passed+failed+skipped`，未改测试口径 |

## 源码修改

无补丁（`patches_applied: []`）。POSIX 兼容的纯 C99 核心库，未引入平台宏。

## 依赖版本

- 无外部编译依赖（核心库 + vendored googletest/nlohmann_json 随源码）
- test_package 运行时仅依赖标准 C 库与 libc++ 上的 `libm`

## 验证结果

首轮仅完成工作树，按任务要求不做本地 conan 构建，等待 HMBS 后台真机预检：

- 上游测试用例通过率：待真机预检回填（conan create 日志实测为准，不估算）
- 新增测试用例通过率：待真机预检回填（`./test_nanoarrow` 4 项检查为准）
- 反证计划（预检通过后由日志佐证）：检查测试输出与参照非空；必要时以 `exit 1` 桩确认 harness 可抓失败；区分通过与静默跳过

## 交付物

| 文件 | 说明 |
|------|------|
| archives/n/nanoarrow/0.9.0/conanfile.py | 主配方（CMake + ctest + HMBS 证据） |
| archives/n/nanoarrow/0.9.0/conandata.yml | 官方 tag URL + sha256 |
| archives/n/nanoarrow/0.9.0/manifest.yaml | 版本级 manifest |
| archives/n/nanoarrow/0.9.0/test_package/ | test.c + CMakeLists + conanfile + MANIFEST |
| archives/n/nanoarrow/manifest.yaml + README.md | 软件级元数据 |

## 注意事项

- 本轮严禁 commit/push/建 PR；工作树保持未提交，等待 HMBS 真机全部门禁
- 上游 IPC/DEVICE 扩展默认关闭：IPC 需 vendored flatcc（源码自带但增加构建面），DEVICE 的 Metal/CUDA 与鸿蒙无关；基础适配先覆盖核心库
- test_package 使用 `can_run` 守卫；原生构建（build=target=OHOS/aarch64）下正常执行
