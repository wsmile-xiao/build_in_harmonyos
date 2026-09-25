# libqes 0.2.8 — HarmonyOS PC 适配记录

- 申请人：momimgya
- 队伍：干
- 上游：https://github.com/kdmurray91/libqes（tag 0.2.8，GPL-3.0-or-later）
- 构建系统：CMake（`CMakeLists.txt` + `src/CMakeLists.txt` + `test/CMakeLists.txt`）
- 依赖：zlib（`FIND_PACKAGE(ZLIB 1.2.5 REQUIRED)`，制品仓 OHOS 已发布 `zlib/1.3.1.1`；不用无 OHOS 二进制的裸 `1.3.1`，否则预检被迫从 conancenter 源码重编依赖并在配方配置前失败）
- 适配动作：
  - `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 `CMAKE_MINIMUM_REQUIRED(VERSION 2.8)` 过老）
  - `NO_OPENMP=True`（OHOS 无 OpenMP 运行时，上游显式支持关闭）
  - 保留 zlib 支持（Conan 提供）
  - `build()` 末尾 `cmake.test()` 运行上游完整 CTest 套件
- 上游测试清点（`test/`，tag 0.2.8）：
  - 测试源：`test.c` `test_file.c` `test_helpers.c` `test_log.c` `test_match.c`
    `test_seq.c` `test_seqfile.c` `test_sequtil.c` `test_util.c` + `helpers.c`
    + `tinytest/tinytest.c`，全部编译进 `test_libqes`
  - CTest 注册（`test/CMakeLists.txt`）：`run_test_libqes`（`test_libqes <bindir>`，
    tinytest 全量用例）、`run_log_demo`（`log_demo`）、`run_bench_libqes`
   （`bench_libqes data/test.fastq 50 ...`，5 组 benchmark 函数）
  - 来源目录：`test/`；`test/data/` 随构建拷贝到 `<build>/data`
- test_package（消费者视角）：`qes_seq_create` / `qes_seq_fill_name` /
  `qes_seq_fill_seq` / `qes_seq_ok` / `qes_seq_destroy` 全链路验证，
  链接 `qes` + `zlib`，断言 8 项
- 真机修复（2026-09-18 预检 upstream_test 失败：`run_bench_libqes` Failed，
  `can't create temporary file /tmp/...: Read-only file system`）：
  `test/benchmarks.c` 的 `bench_qes_seqfile_write` 用 `tmpnam(NULL)` 硬编码
  `/tmp`，只读挂载下 `qes_file_open` 走默认 `errprintexit` 直接退出；
  在 `source()` 中精确替换该单行为优先使用配方注入的可写
  `TMPDIR/TMP/TEMP`（回退 `/tmp`），仅替换临时文件根目录，不删测试、
  不改断言（此前两轮曾用 conandata 补丁文件，先后因上下文错位与补丁流
  解析失败而未通过，故改用 Python 精确字符串替换策略，效果等价但不再
  受 unified-diff 行号/空行计数影响）
- 证伪计划（真机预检返回后核对）：确认 `ctest` 输出非空且 3/3 通过；
  若出现 0 测试或静默跳过，按守则把被测二进制换桩重跑确认 harness 有效
