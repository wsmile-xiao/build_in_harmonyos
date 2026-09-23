# liboop 1.0.1 适配笔记

liboop 是 POSIX 事件循环底层库（select/定时器/信号/fd 注册），上游主页
http://www.lysator.liu.se/liboop/ ，源码包
https://ftp.lysator.liu.se/pub/liboop/liboop-1.0.1.tar.gz
（sha256 56af16ad65e7397dadc8268e37ff6f67431db390c60c75e21a33e12b0e0d17e0，
39 个条目）。

## 上游测试审计结论

上游确无自动化测试（`upstream_tests_exist: false`，详见
test_package/MANIFEST.yml 的 `upstream_test_audit`）：

- 39 条目逐项核对：无 tests/test/t/spec 目录，无 `*test*`/`*check*` 测试源
  （仅 `test-oop.c` 手动交互示例，非自动化套件）；
- `Makefile.am` 无 `TESTS`/`check_PROGRAMS`/`check-local` 定义；
- `configure.ac` 无 `enable_testing`/`add_test`、无 gtest/ctest/pytest 注册；
- `make check` 为 automake 默认 no-op；`build()` 不集成 `make check`
 （`upstream_test_in_build: false`），证据由 test_package 每轮复发
  `status: no_tests` 标记给出。

## 配方要点

- Autotools 核心库单构建：`--without-adns --without-readline --without-glib
  --without-tcl`（不启用 `--with-libwww`），零 Conan 依赖；
- `settings` 四项齐全（os/compiler/build_type/arch），`validate()` 用
  `in ("Linux", "OHOS")`（R32）；
- HMDFS 硬化：`ac_pwd` 回退 `$PWD`、构建前 `chdir` + 导出 `PWD`、
  可写 `TMPDIR`、`/bin/sh` 回退（autoconf 2.69 同 backuppc-rsync 家族）；
- E007：2014-03-23 版 `config.guess` 为 `echo/exit` 风格（前 GUESS= 重构），
  按 gtypist/btparse 同款补 `*:HarmonyOS:*:*)` 分支原生输出
  `aarch64-unknown-linux-ohos`，`config.sub` 接受 `linux-ohos`，
  `generate()` 剥离 `--build/--host`（R15，避免伪交叉）；
- 沙箱 CC：profile 硬编码 `/data/service/hnp/bin/clang` 在预检沙箱内
  `inaccessible or not found`（exit 127），按 juise 3.0.0 同款
  `shutil.which(clang)` 优先、再取 `tools.build:compiler_executables`
  字典回退，`CC/CXX/AR/RANLIB` 内联前缀 + 改写 `conanbuild.sh`
  双通道强制生效（零依赖，无 LD_LIBRARY_PATH 遮挡问题）；
- `package()` 清理 `*.la`，`liboop.pc` 前缀改写为 `${pcfiledir}/../..`，
  `package_info()` 提供 `cmake_file_name=liboop` /
  `cmake_target_name=liboop::liboop` / `pkg_config_name=liboop`。

## test_package 设计（R34）

CMake 消费者 `test_liboop` 直链 `liboop::liboop`，覆盖 6 项真实断言：

1. `oop_sys_new` 非空；
2. `oop_sys_source` 接口 6 函数指针非空；
3. 自定义 `oop_malloc/realloc/free` 生效；
4. 定时器注册后取消，`oop_sys_run_once` 返回 `OOP_CONTINUE`；
5. 管道 fd 注册后取消 + `SIGUSR1` 注册后取消；
6. `oop_select`/`oop_signal` 适配器创建删除。

每项打印一行 `CHECK-OK:`，`test()` 计数 `CHECK-OK` 行数产生
`HMBS_TEST_PACKAGE_RESULT(discovered=6)`；上游标记每轮复发
`HMBS_UPSTREAM_TEST_RESULT(status=no_tests, discovered=0, executed=0)`，
缓存命中轮次同样有效。

## 真机失败诊断（2026-09-18 预检，test_package，exit 137 / Signal 9）

- 现象：`RUN: ./test_liboop` 后仅见 `CHECK-OK: sys-new`，随后 `Signal 9`，
  `conan create` 以 137（128+9，SIGKILL）退出；`preflight.sh[306]` 读
  `/proc/<pid>/cmdline` 失败（被杀进程已消失的竞态）。
- 定性：SIGKILL 不能由用户态坏指针产生（坏指针给 SIGSEGV/SIGBUS），只能来自
  外部 kill / 超时杀 / OOM / seccomp。结合“首行后无输出即被杀”，最可能的是
  某处阻塞致预检超时杀，或后续步骤被杀；摘要为省略式（中间行可能被折叠），
  无法从摘要精确定位到第 2 步。
- 另有证据流缺陷：旧 `test()` 先裸调 `self.run(..., env="conanrun")`，二进制
  一崩即抛异常，两个 HMBS 标记都发不出（故解析出上游发现 0）；且 C 输出全缓冲，
  被 SIGKILL 时缓冲区证明全丢。

## 本轮修复（断言未减，6/6 口径不变）

1. `test_liboop.c`：`setvbuf(_IONBF)` + 每个 `CHECK-OK` 后 `fflush`，被杀时已
   打印行必留痕，下轮日志可精确定位；
2. `test_liboop.c`：第 4 步 `oop_sys_run_once` 加 10s 有界保护（sigaction 装
   SIGALRM，不带 SA_RESTART 使 select 以 EINTR 返回；超时则显式 FAIL 而非静默
   挂起；通过路径 alarm 永不触发，行为零变化）；
3. `test_package/conanfile.py`：审计型 `HMBS_UPSTREAM_TEST_RESULT(no_tests)`
   改为 `test()` 首发（先于二进制运行，崩溃也留痕）；conanrun 首跑改为
   try/except 记录后必进计数跑，任何失败都先发 `HMBS_TEST_PACKAGE_RESULT
   (passed=false)` 再抛异常，杜绝“无标记 0 发现”。

## 待真机验证

- HMBS 预检（conan create + test_package + no_tests 标记）结果以 hmbs
  后台复跑日志为准；本轮仅交付工作树，未提交。
