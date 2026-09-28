# sockpp 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++（`/data/service/hnp/bin`，profile `ci/conan/profiles/ohos-aarch64`：os=OHOS、arch=armv8、cppstd=17、libc++）
- 状态: built

## 基本信息

- 分支：`feat/sockpp-1.0.0`（分支门禁：去 `feat/` == 包目录名-版本 `sockpp-1.0.0`）
- 包目录：`archives/s/sockpp/1.0.0/`（上游 `upstream/main` 无此包目录，属**全新包**，`task_init.sh --allow-unpublished` 放行）
- 上游：https://github.com/fpagliughi/sockpp ，tag `v1.0.0`（`git ls-remote --tags` 实证 `e6c4688a576d95f42dd7628cefe68092f6c5cd0f`）
- 源码包：https://github.com/fpagliughi/sockpp/archive/refs/tags/v1.0.0.tar.gz ，114358 字节（约 114KB），sha256 `818477fae6eb29b9daacef71a3d0c494de9e48f6fd267a7fc5a4c332db211bc5`（与 CCI `conan-center-index/recipes/sockpp/all/conandata.yml` 逐字一致）
- 许可证：BSD-3-Clause；运行期依赖 0；测试依赖 Catch2（`test_requires`）

## W0 生死关结论（全过）

| 关 | 取证 | 结论 |
|---|---|---|
| 版本可得性 | `git ls-remote --tags https://github.com/fpagliughi/sockpp` 出现 `refs/tags/v1.0.0` | 通过 |
| sha256 多路取证 | 本机下载重算 == CCI conandata == 任务卡记录（`818477fa…`），三处同源 | 通过 |
| 硬依赖在档 | `conan list -r=ohpcd "catch2/*"` → 3.16.0 / 3.8.1 / 2.13.10 / 2.13.10-r0，`catch2/3.8.1` 有 ohos-aarch64 二进制（`4b977264…`）；运行期依赖 0 | 通过 |
| 平台可移植（ISA/printf） | 源码全树 grep `altivec\|mmx\|3dnow\|immintrin\|x86intrin\|arm_neon\|cpuid` 与 `register_printf\|printf.h` 均 0 命中 | 通过 |

## 编译步骤

1. 手工探索（SKILL Step 2）：
   ```bash
   cmake -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release \
     -DSOCKPP_BUILD_SHARED=ON -DSOCKPP_BUILD_STATIC=OFF -DSOCKPP_BUILD_TESTS=ON
   cmake --build <build> -j4 && cmake --install <build>
   ```
   configure / build / install 三步 rc=0，安装树含 `include/sockpp/*.h`（含生成的 `version.h`）、`lib/libsockpp.so`、`lib/cmake/sockpp/*.cmake`。
2. 上游单测探索：`ctest` 在 `<build>/tests/unit` 内执行 → `100% tests passed, 0 tests failed out of 33`；直接跑 `unit_tests` → `All tests passed (236 assertions in 33 test cases)`。
3. Conan 配方：`conan create archives/s/sockpp/1.0.0 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 -c tools.build:jobs=4` → 配方构建 + 上游 CTest + `test_package` 消费者测试全链 rc=0。
4. 采信轮与收尾按工作区固序执行（`tools/conan_verify_round.sh` → `finish built` → `finish_restore.sh --apply` → `capture_evidence.py --verify`），读数见 `reports/` 与 `final-report.md`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `readelf -d libsockpp.so` 无 `SONAME` 条目，共享库丢失 DT_SONAME | conan `CMakeToolchain` 不写 `CMAKE_SYSTEM_NAME`，CMake 退回 `uname=HarmonyOS` 打印「System is unknown to cmake」，平台模块缺失使 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 等变量为空 | 按知识条目 **E092**（`rec_priority=1`）在 `generate()` 钉 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`；修后 `readelf -d` 出现 `SONAME: libsockpp.so.1` |
| 2 | 在构建根目录跑 `ctest` 打印 **`No tests were found!!!` 且 rc=0**（假绿） | 上游只在 `tests/unit/CMakeLists.txt` 里 `include(CTest)`/`catch_discover_tests`，顶层 `CMakeLists.txt` 从不 `enable_testing()` ⇒ 根目录根本不生成 `CTestTestfile.cmake`，ctest 无测试可跑仍返回 0 | 配方改为 `self.run("ctest …", cwd=<build>/tests/unit)`，并在子目录先 `ctest -N` 打印 `Total Tests: 33` 留证；`unit_tests` 聚合摘要另行落日志，任一失败即抛异常 |
| 3 | 源码 `TEST_CASE` 宏 43 个，实际只注册执行 33 个 | ① `tests/unit/CMakeLists.txt` 的 `add_executable` 未收录 `test_inet6_address.cpp`（6）与 `test_result.cpp`（2），上游自身也不编译；② `test_socket.cpp` 的「thread-safe last error」与 `test_stream_socket.cpp` 的「stream_socket address constructor」位于 `#if 0` 死块 | 按 §3.5 取候选数最大值 **N=43** 为上游总数，实际运行 **N′=33**，10 个未运行逐项归因（8 个上游未构建 + 2 个死块），`TOTAL = PASS 33 + FAIL 0 + SKIP 0 + NOT_RUN 10 = 43` |
| 4 | `test_package` 首轮 `FAIL assertion #7: loopback.address() == INADDR_LOOPBACK` | 自身测试写错字节序：`inet_address::create()` 内部做 `htonl(addr)`，构造参数应是**主机序**，我传了网络序 | 构造改传 `INADDR_LOOPBACK`；`resolve_name()` 保持与上游 `test_inet_address.cpp` 同口径比较 `htonl(INADDR_LOOPBACK)`（上游测试原文如此） |

补充（环境探测，非阻塞）：`gethostbyname("localhost")` → `127.0.0.1`、`bind 127.0.0.1:12345` 成功、AF_UNIX `bind("/tmp/…")` 报 `EROFS`（`/tmp` 只读）。上游单测**不 bind 任何 AF_UNIX 路径**（`test_unix_address.cpp` 只构造地址对象，stream/dgram 用 `socketpair()`），TCP 用例改由本配方以**端口 0 临时端口**方式在 `test_package` 侧验证，因此套件在设备上不需要可写 `/tmp`。

## 源码修改

无。上游 1.0.0 在本设备 configure/build/install 与单测全绿，未打任何补丁（`patches/` 为空，`conandata.yml` 无 `patches:` 段）。

## 依赖版本

- 运行期：无
- 构建期（`test_requires`，不传播给消费者）：`catch2/3.8.1`（来自 ohpcd 远端，含 `lib/cmake/Catch2/Catch.cmake` 供上游 `include(Catch)` 使用）
- 构建工具：设备自带 cmake 4.1.2、GNU Make 4.4.1、clang/clang++ 15.0.4

## 验证结果

```bash
# 采信轮（工作区固序，overlay 入口）
sh "$WORKSPACE_ROOT/tools/conan_verify_round.sh" sockpp 1.0.0 \
  --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
# → rc=0（干净轮：构建标志计数 run_make=8 / calling_build=2 / apply_patch=0，DB 两表清净）
# finish sockpp 1.0.0 built → rc=0
sh "$WORKSPACE_ROOT/tools/finish_restore.sh" --apply "$TASK_DIR" "$TARGET_REPO" "$PACKAGE_DIR"
# → ✅ finish 副作用已全部还原（conandata.yml 镜像改写、SUMMARY.md、notes.md 三处回滚）
python3 "$WORKSPACE_ROOT/tools/capture_evidence.py" --verify "$TASK_DIR/evidence-index.json"
# → 3/3 证据与副本一致（conan-create.log / conan-verify-report.md / w3-local-ci.log）

# 门禁读数（reports/conan-verify-report.md，干净轮原文）
# Verdict: PASS（部分跳过，需人工补测: L2, L4）
# G0 PASS（E092 已在配方中处理）· G1 PASS · G2 PASS · G3 PASS · G4 PASS（lib 1 .a + 0 .so、include 28 头文件）
# L2 SKIP（纯库包无 bin/）· L4 SKIP（无可扫描 ELF）→ 人工补测见 reports/conan-verify-supplement.md
# L5 PASS（首次基线 32 文件）

# 上游单测（conan create 日志内，最终设备日志）
ctest -N                       # Total Tests: 33
ctest --output-on-failure -j1  # 100% tests passed, 0 tests failed out of 33
./unit_tests                   # All tests passed (236 assertions in 33 test cases)
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "catch2", "discovered": 33, "executed": 33, "passed": 33, "failed": 0, "skipped": 0, "assertions": 236}

# test_package 消费者测试（conan create 日志内）
sockpp test passed! check_summary: 20 assertions OK, version v1.0.0
```

上游测试计数口径（同一统计单位，四口径分列不混用）：

- 源码宏数（`TEST_CASE(` 清点，候选数法最大值）= **43**
- 框架注册数 / 实际运行数 = **33**（`ctest -N` 与 Catch2 聚合摘要一致）
- 本次执行 assertion 数 = **236**（源码 `REQUIRE(` 296，差额来自未收录文件 59、死块 11，另有 SECTION 逐分支执行带来的重复计数，属不同口径不混算）
- `test_package` 消费者断言 = **20**（计入「鸿蒙特有测试」行，不进上游分母）

## 注意事项

- 上游 `tests/CMakeLists.txt` 不存在（只有 `tests/unit/`），`SOCKPP_BUILD_EXAMPLES` 必须保持 OFF（examples 需要额外资源）。
- `test_package` 使用端口 0 由内核分配临时端口，避免与设备上其它任务争抢固定端口。
- 本包为纯库包，无 `bin/`，按 PF8/R38 **不创建** `commands.json`。
