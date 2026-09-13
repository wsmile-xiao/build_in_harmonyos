# gperftools 2.17.2 适配笔记

## 当前状态

- 目标平台：HarmonyOS PC aarch64/OHOS
- 构建系统：Autotools
- 当前状态：built（设备 W3、Conan 验证和消费者测试已通过），尚未 published；finish 外层仅留下已登记的 submit-only/ SUMMARY 白名单警告，副作用已还原
- 默认 Conan 配置：静态 `tcmalloc_minimal`、无 Conan 依赖、C++17

## 源码与补丁

- 官方 release tarball：`gperftools-2.17.2.tar.gz`
- `0001-config.guess-ohos.patch`：让 release 自带 `config.guess` 将
  `aarch64:HarmonyOS` 映射为 `aarch64-unknown-linux-ohos`。
- `0002-configure-umask-ohos.patch`：绕过生成的 `configure` 中在 HMDFS 上不可写的
  `mktemp -d` 私有目录分支，改用 `umask 022` 下的显式 `mkdir` 临时目录。
- `0003-generic-writer-test-tmpdir.patch`：设备 `/tmp` 实测 100% 满且不可写，musl
  `tmpfile()` 不读取 `TMPDIR`；将 `generic_writer_test` 改为使用 `TMPDIR` 下的
  `mkstemp`，创建后立即 unlink，保持测试的匿名临时文件语义。
- `0004-gtest-tempdir-ohos.patch`：让 vendored GoogleTest 的捕获流临时文件使用
  `TempDir()` 返回的 `TEST_TMPDIR/TMPDIR`，覆盖设备上的可选 debugalloc 测试，
  不引入平台专用宏。
- `0005-heap-profiler-test-tmpdir-ohos.patch`：让 heap-profiler 脚本在设备可写的
  `TMPDIR` 创建临时目录。
- `0006-profiler-pprof-units.patch` 与 `0007-profiler-pprof-cumulative.patch`：兼容
  上游文档指定的 Go `pprof` 输出（带 `ms` 等单位，跨线程函数可能只出现在 cumulative 列），
  不改变被测 profile 数据或通过条件。
- `0008-profiler-cpu-timer.patch`：完整套件为 profile-handler 回归测试提供
  `CPUPROFILE_REALTIME=1` 时，profiler 脚本先恢复其 CPU-timer 默认路径；脚本自身仍单独覆盖
  realtime 分支。
- release 中的 `config.sub` 已经包含 `ohos*` 与 `linux-ohos*`，因此没有重复补丁。

## Conan 工作目录

设备 v13 的原始 `conan create` 曾因 HMDFS 的 `getcwd(2)` 返回失败而中止，
配方在 OHOS 构建阶段导出 `PWD=self.build_folder` 后已修复。W3 v19 曾在前一
SHA 上完成源码、补丁、native、Conan、consumer 和 repo snapshot；随后当前收尾
轮也重新完成了同一链路，`make check` 为 29/29，`conan test_package` 消费者为
1/1。随后 finish/built 的内嵌 Conan/W3 也通过；外层退出码仅受已登记的
submit-only 与 SUMMARY 白名单步骤影响，未将此误报为构建失败。

## 构建与测试口径

配方执行以下上游测试链：

```text
configure -> make -j1 -> make -j1 check
```

`test_package` 使用 CMake `find_package(gperftools CONFIG REQUIRED)`，链接
`gperftools::tcmalloc_minimal`，并运行 `tc_version`、分配/重分配/释放以及
`tc_malloc_size` 的真实运行时检查。实际数量和状态记录在版本 manifest；原始设备
输出保存在任务私有 W3 证据目录，不进入 PR。

## 已知边界

- 默认 Conan 包仍是静态 `tcmalloc_minimal`，其 W3 `make check` 为 29/29；另以
  `--enable-minimal=no --enable-cpu-profiler=yes --enable-heap-profiler=yes
  --enable-debugalloc=yes` 的完整上游配置验证 53/53，测试总计为
  `TOTAL=53 PASS=53 FAIL=0 SKIP=0 NOT_RUN=0`，退出码 0。
- 完整配置使用设备任务私有前缀构建的无 cgo Go `pprof`，并设置
  `CPUPROFILE_REALTIME=1 PPROF_BINARY_PATH=$PWD TCMALLOC_STACKTRACE_METHOD=generic_fp`；
  该环境只用于全量上游测试，不改变默认 Conan 产物。
- 未创建 `commands.json`：release 的 Autotools 默认安装产物是库和头文件，不是命令行工具。
