# finalcut 0.9.1 上游测试台账

## 清点依据

- 官方源码：`https://github.com/gansm/finalcut/archive/0.9.1.tar.gz`
- SHA256：`6593b3c43ba1de98e4e0e3a563dbf9316fade71ef85c82e6b6f086184ec69a56`
- 清点位置：发布归档 `test/Makefile.am` 的 `TESTS` 与 `noinst_PROGRAMS`，共 30 个目标。
- 目标：HarmonyOS 6.0 aarch64，Clang 15.0.4/libc++；使用已发布的 CppUnit 1.15.1 与 ncurses 6.6。
- 适配后完整目标命令：`make -j1 check`，已由 Conan `build()` 自动运行并在真机完整执行通过；实测 `TOTAL 28 / PASS 28 / FAIL 0 / ERROR 0`。使用串行构建是为了避开设备 HNP 临时目录不允许创建 GNU make 并行 jobserver FIFO 的环境限制。
- 上游 Makefile 漏传 `CPPUNIT_CFLAGS`；测试配置额外通过 `CPPFLAGS` 指定 CppUnit 与 ncurses include 目录。终端用例设置 `TERMINFO` 指向 ncurses Conan 包自带数据库。以上仅为测试环境变量，不改变生产配方。

## 原始上游未适配基线

在应用 `0006` 前，设备上的 30 个目标实测为 PASS 21、运行时 FAIL 2、构建/链接 BLOCKED 7。原因包括 HarmonyOS 不提供 FreeBSD/OpenBSD 后端、测试配置没有启用 `DEBUG`/`UNIT_TEST`、静态链接时重复定义 helper、aarch64 long-double 精度与固定 x86 字符串不同，以及 Sun/screen termcap 测试依赖具体数据库/状态。下表记录的是应用补丁后的逐项结果。

## 逐项结果

| # | 上游源文件 | 目标/命令 | 结果 | 证据/说明 |
|---:|---|---|---|---|
| 1 | `test/char_ringbuffer-test.cpp` | `char_ringbuffer_test` | PASS | 构建、运行通过 |
| 2 | `test/fcallback-test.cpp` | `fcallback_test` | PASS | 构建、运行通过 |
| 3 | `test/fcolorpair-test.cpp` | `fcolorpair_test` | PASS | 构建、运行通过 |
| 4 | `test/fdata-test.cpp` | `fdata_test` | PASS | 构建、运行通过 |
| 5 | `test/fevent-test.cpp` | `fevent_test` | PASS | 移除与库内 friend helper 的重复定义；静态链接成功并运行通过 |
| 6 | `test/fkeyboard-test.cpp` | `fkeyboard_test` | PASS | HarmonyOS 门控后运行 4 个无交互依赖用例；9 个依赖 TIOCSTI 的输入注入用例因内核拒绝该 ioctl 而不注册。Release 下回调复制导致夹具初始化 SIGSEGV；配方仅给 OHOS Clang 的 `FKeyboardTest::init()` 添加 `optnone`，此目标 4/4 通过 |
| 7 | `test/flogger-test.cpp` | `flogger_test` | PASS | 构建、运行通过 |
| 8 | `test/fmouse-test.cpp` | `fmouse_test` | PASS | 构建、运行通过 |
| 9 | `test/fobject-test.cpp` | `fobject_test` | PASS | 构建、运行通过 |
| 10 | `test/foptiattr-test.cpp` | `foptiattr_test` | PASS | 构建、运行通过 |
| 11 | `test/foptimove-test.cpp` | `foptimove_test` | PASS | 指向 ncurses terminfo 后构建、运行通过；未设置时曾因找不到 terminal database 中止 |
| 12 | `test/fpoint-test.cpp` | `fpoint_test` | PASS | 构建、运行通过 |
| 13 | `test/frect-test.cpp` | `frect_test` | PASS | 构建、运行通过 |
| 14 | `test/fsize-test.cpp` | `fsize_test` | PASS | 构建、运行通过 |
| 15 | `test/fstring-test.cpp` | `fstring_test` | PASS | 34 项通过；浮点断言改为比较目标精度往返，不固定 x86 long-double 文本 |
| 16 | `test/fstringstream-test.cpp` | `fstringstream_test` | PASS | 构建、运行通过 |
| 17 | `test/fstyle-test.cpp` | `fstyle_test` | PASS | 构建、运行通过 |
| 18 | `test/fterm_functions-test.cpp` | `fterm_functions_test` | PASS | 构建、运行通过 |
| 19 | `test/ftermcap-test.cpp` | `ftermcap_test` | PASS | 设置 ncurses `TERMINFO` 后构建、运行通过；未设置时曾因找不到 terminal database 中止 |
| 20 | `test/ftermcapquirks-test.cpp` | `ftermcapquirks_test` | PASS | 12 项通过；capability 名称精确匹配，fallback 清理 tmux 状态并独立检查 |
| 21 | `test/ftermdata-test.cpp` | `ftermdata_test` | PASS | 构建、运行通过 |
| 22 | `test/ftermdetection-test.cpp` | `ftermdetection_test` | PASS | 开启测试专用 DEBUG 后构建并运行通过 |
| 23 | `test/ftermfreebsd-test.cpp` | `ftermfreebsd_test` | N/A | 验证 FreeBSD/DragonFly 专属终端后端；Automake 仅对这些 native host 注册，HarmonyOS 不提供该后端 |
| 24 | `test/ftermlinux-test.cpp` | `ftermlinux_test` | PASS | 设置 ncurses `TERMINFO` 后构建、运行通过 |
| 25 | `test/ftermopenbsd-test.cpp` | `ftermopenbsd_test` | N/A | 验证 OpenBSD 专属终端后端；Automake 仅对 OpenBSD native host 注册，HarmonyOS 不提供该后端 |
| 26 | `test/ftimer-test.cpp` | `ftimer_test` | PASS | 构建、运行通过 |
| 27 | `test/fvterm-test.cpp` | `fvterm_test` | PASS | 开启 UNIT_TEST 接口并修正测试桩 const 签名；完整运行通过 |
| 28 | `test/fvtermattribute-test.cpp` | `fvtermattribute_test` | PASS | 构建、运行通过 |
| 29 | `test/fvtermbuffer-test.cpp` | `fvtermbuffer_test` | PASS | 构建、运行通过 |
| 30 | `test/fwidget-test.cpp` | `fwidget_test` | PASS | 开启 UNIT_TEST 后 FApplication::start 测试接口可用；运行通过 |

## 适配结果与独立 Conan 测试

- 原始发布归档共注册 30 个跨平台目标。HarmonyOS aarch64 Conan Release 实测为 28/30：完整 `make -j1 check` 报告 28 个适用目标、28 PASS、0 FAIL、0 ERROR；FreeBSD/OpenBSD 两个专用后端目标按 host 条件不注册，计为 2 个 N/A，不计为 PASS。
- `fkeyboard_test` 的 CppUnit 测试共 13 个；HarmonyOS 内核拒绝 `TIOCSTI`（`ioctl` 输入注入），因此只注册并运行 4 个无交互依赖用例，9 个输入注入用例明确不在 HarmonyOS 上运行。其他平台仍运行完整键盘测试。
- Conan consumer：`test_finalcut` PASS；`test_ohos_unicode` PASS；共 2/2。鸿蒙专项测试经 PTY 完成 FINAL CUT 界面启动、CJK 显示与输入、Tab/回车按钮操作及正常退出；本次真机 Conan rerun 约 1.52 秒。
- HarmonyOS 专属 consumer 使用 `C.UTF-8`，通过 PTY 实际运行 FINAL CUT 对话框，显示并键入 CJK“鸿蒙”，切换焦点后激活 Accept；退出时核验宽字符长度和 UTF-8 内容。
