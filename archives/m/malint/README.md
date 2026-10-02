# malint

**MPEG Audio 流校验器** — 解析 MPEG 音频流（MP1/MP2/MP3，含 VBR、id3v1/id3v2），打印流信息与格式违规报告。

- 上游主页：https://www.nih.at/malint/
- 许可证：GPL-2.0-or-later
- 版本：0.2（autotools 构建）

## 产物

| 产物 | 说明 |
|------|------|
| `bin/malint` | MPEG 音频流校验命令行工具（`malint -N3 file.mp3`） |

## OHOS 适配要点

- 官方 tarball 由 autoconf 2.59 生成，自带 configure/Makefile.in，无需 bootstrap；
  但不含 config.guess/config.sub，configure 显式传 `--build/--host`
  （aarch64-unknown-linux-gnu）规避宿主类型猜测失败（E007 同类）。
- HMDFS setgid 目录按组权限判定写入：autoconf 以 `umask 077` 创建的临时目录
  在真机上导致 config.status Permission denied（E011/E052 同类）；配方对
  configure/make/check/install 统一以 `umask 022` 运行（构建环境层，非源码补丁）。
- 纯 C、无第三方依赖：musl libc 自带 strerror/getopt，configure 的 LIBOBJS
  替换（strerror.c/getopt.c）不启用，无需源码补丁。
- 设备故障期适配（真机实测，已固化进配方）：shell 经 shutil.which 校验回退，
  configure 由解释器直接执行（绕开 /bin/sh shebang，E087）；`make SHELL=`、
  `make check TESTS_ENVIRONMENT=sh`（HMDFS 无执行位，E046）；`TMPDIR/TMPPREFIX`
  指向可写目录（/tmp 只读，E002）；CC 从 Conan conf 显式注入（R33）。

## 测试统计（双口径）

- source_declared_total = 6（regress/runtest 用例）
- configured_executable_total = 6（regress/Makefile.am TESTCASES）
- executed_passed_total = 6（真机 shadow CI `make check` 6/6 PASS）
- test_package 消费者验证 PASS；L0/L1/L2/L4/L5 全 pass
- 详情见 `0.2/manifest.yaml` 与 `0.2/notes.md`
