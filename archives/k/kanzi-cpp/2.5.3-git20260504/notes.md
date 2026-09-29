# kanzi-cpp 2.5.3-git20260504 适配笔记

## 基本信息

- 上游：https://github.com/flanglet/kanzi-cpp（Apache-2.0）
- 版本：2.5.3-git20260504（master 快照 f68e09f，2026-05-03，与 Debian
  `2.5.3+git20260504` 同源；快照内 CMakeLists 工程版本仍为 2.5.1，
  app 内的 `KANZI_VERSION` 已为 2.5.3，属上游版本号未同步，目录版本
  以任务命名为准）
- 构建系统：CMake（>= 3.10），C++17，依赖 Threads（OHOS libc 提供）
- 源码包：`f68e09f....tar.gz`（355119 字节，
  sha256 `f85ec7ccbf855494093de95548abee777ae42d7cf2bcfa2aa8ab3d768022858c`）
- 依赖：无（零第三方依赖）
- 状态：built（待真机 rule4 门禁通过后由 HMBS 提交）

## 适配决策

| # | 决策 | 依据 |
|---|------|------|
| 1 | `KANZI_ENABLE_NATIVE_OPTIMIZATIONS=OFF` | 上游默认 ON 会追加 `-march=native`；关闭后输出通用 armv8，保证不同机器可复现 |
| 2 | 声明标准 `shared` 选项（默认 False） | Conan 2 要求 package_type=library 必须声明 shared 选项；上游恒产出 static（libkanzi.a）+ shared（libkanzi.so）+ kanzi/kanzi_static 工具，两者都打包（选项取值不改变产物） |
| 3 | 1 个可移植补丁：`patches/testapi-tmpfile-tmpdir.patch`（仅测试辅助） | 2026-09-28 真机 7/8：API 条目 `ASSERT FAILED: fmemopen failed (TestAPI.c:106)`；`portable_fmemopen()` 用 `tmpfile()`（写死 `/tmp`、忽略 HMBS 注入的 `$TMPDIR`），在 HarmonyOS 沙箱返回 NULL；补丁保留 `tmpfile()` 首选，仅失败时回退到 `TMPDIR/TMP/TEMP` 感知的 `mkstemp`（立即 `unlink` 保持匿名语义），不断言删减、不跳过 |
| 4 | 不声明 `commands.json` | 配方为 `package_type="library"` 且未声明非空 bindirs，L0k 按库处理；随包附带的 kanzi 工具仅用于消费者验证 |
| 5 | conandata 仅官方 URL | R39 + 审查规则：CI 自动加镜像回退；本次 github.com 直连下载正常（355KB），无超时证据，不手动加镜像 |
| 6 | 真机 OOM 时加法式 `-O1 -g0`（`tc.extra_cflags/cxxflags + OHOS build-env CFLAGS/CXXFLAGS append + conan_toolchain.cmake tail HMBS_OOM_MITIGATION`）+ 本轮补 `source()` 内上游 `-O3→-O1 -g0` 原地降级（OHOS 限定） | 2026-09-23 预检 compile 期 `tar: Cannot fork: Out of memory`（源码包仅 355KB，非包体积问题，系编译期内存压力致后续 fork 失败）；HMBS 已注入 jobs=1，在 profile `-O3` 之后追加，尾部 `-O1` 生效、`-g0` 去调试信息，不覆盖 profile、不跳过任何测试；2026-09-28 仍 Signal 9 空日志，核查上游 CMakeLists 发现 `set(COMMON_FLAGS "-Wall -Wextra -O3 ...")` 在工具链之后追加，工具链 `-O1` 被反超而失效，故必须在源码侧降级，上游其它旗标（-Wall/-Wextra/-fPIC/-DNDEBUG/-fno-rtti）保留；2026-09-29 补 build() 内 OHOS 单作业 cmake.build（--parallel 1/-j1，oystr 先例），与 HMBS 注入 jobs=1 对齐、防 CI 侧高并行复发 fork OOM，不跳过任何测试 |
| 7 | OHOS 下 `CMAKE_SYSTEM_NAME=Linux` + `PROCESSOR=aarch64` + `POLICY_MINIMUM=3.5`（`tc.cache_variables`，主包与 test_package 同步）+ 可用编译器探测、命令行双钉与生成工具链文件原地修正 | 2026-09-24 三轮 configure 失败：首轮 `System unknown/Platform/HarmonyOS`，次轮加别名后仍 `compiler identification is unknown`，第三轮 harmonybrew 已探测成功但 `project()` 仍用 `/data/service/hnp/bin/clang`；E092 + zydis/kyoto-tycoon 先例：cache/命令行单钉盖不住工具链默认值，故加 `_fix_generated_toolchain_compiler` 原地替换 `conan_toolchain.cmake` 并导出 CC/CXX（仅配置路径缺失且解析路径存在时） |

## 上游测试（8 ctest entries，口径 ctest_entries）

顶层 CMakeLists 无条件构建 8 个测试可执行文件并注册 8 个 add_test：
BWT、Transforms、EntropyCodec、DefaultBitStream、Factories、
MalformedStream、CompressedStream、API。`build()` 中以
`ctest --output-on-failure` 实际运行，从
`Testing/Temporary/LastTest.log` 逐行解析
`N/M Testing: <name>` + `Test Passed./Failed.` 得出计数并输出
`HMBS_UPSTREAM_TEST_RESULT`（单数据源，无 stdout 猜数）。

## test_package（2 ctest 用例）

1. `roundtrip`：test_kanzi_roundtrip.cpp——64 KiB 确定性载荷经
   `CompressedOutputStream(HUFFMAN + RLT+TEXT)` 压缩，再经
   `CompressedInputStream` 解压，5 项 CHECK（非空、变小、等长、
   读写计数一致、逐字节相等）。
2. `cli_roundtrip`：cli_test.cmake——调用打包产物 `kanzi -c/-d`
   对确定性 ~100 KiB 文件往返并 `compare_files` 逐字节比对
   （`-f` 避免重复运行时交互阻塞）。

## 待真机验证

- `conan create` 全链路（含上游 8/8 + 新增 2/2）留待 HMBS 真机预检；
  本轮仅完成未提交工作树，不猜测通过率数字。
- R26：`kanzi` 非系统同名库，保留 shared；包内无 `/lib` 冲突。
