# DRAFT-libopaque-1.0.1-munit-tmpfile-redirect-tmpdir-shim
> 只读/tmp下munit经tmpfile缓冲stderr失败时构建期-Dtmpfile重定向到TMPDIR兼容
## 问题特征（真实日志片段/标记）
- 真机upstream_test阶段32个munit用例全报（1个end-to-end program + 32 munit matrix，上游标记1/33通过）：
- `libopaque/1.0.1: [upstream]   pwdU=, idU=user, idS=, type=0      Error: unable to create buffer for stderr: Permission denied (13)`（type 0/1/2/3，user/server共32行同错）
- 平台能力：`HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":"/storage/Users/currentUser/preflight/clients/f230079f9361/runtime/libopaque-1.0.1/tmp",...}`，真机/tmp只读，可写TMPDIR已透传
- 修复后构建日志：`RUN: .../bin/cc -O2 -std=c99 -D_POSIX_C_SOURCE=200809L -D_XOPEN_SOURCE=700 -c '.../build-release/upstream/hmbs_tmpfile_shim.c' -o '.../hmbs_tmpfile_shim.o'`；`[ok] built TMPDIR-aware tmpfile shim: .../hmbs_tmpfile_shim.o`
- 修复后测试标记：`HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "munit+ctest", "command": "./opaque-test && ./opaque-munit --fatal-failures (upstream src/tests/, 1 end-to-end program + 32 munit matrix cases)", "discovered": 33, "executed": 33, "passed": 33, "failed": 0, "skipped": 0}`
## 根因
- OHOS libc tmpfile()硬编码/tmp并忽略TMPDIR，真机/tmp只读导致EACCES；证据：musl `src/stdio/tmpfile.c: char s[] = /tmp/tmpfile_XXXXXX（忽略TMPDIR）`
- munit每例调用一次tmpfile()缓冲stderr，失败即MUNIT_ERROR；证据：`munit.c: stderr_buf = tmpfile(); 失败即MUNIT_ERROR`，故32例全部error而非协议失败
- 同PR伴生证据（attempt 20105）：libopaque 1.0.1调用裸名expand_message_xmd而内嵌liboprf 0.9.4已更名为oprf_expand_message_xmd且6参签名一致，仅该符号改名，其余oprf_/toprf_/voprf_hash_to_group未变，真机链接报`ld.lld: error: undefined symbol: expand_message_xmd referenced by opaque_opaque.c.o:(opaque_Register_core/deriveKeyPair)`
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. `archives/l/libopaque/1.0.1/conanfile.py`新增`_build_tmpfile_shim`：构建期生成`hmbs_tmpfile_shim.c`，经`mkstemp($TMPDIR/$TMP/$TEMP)+unlink+fdopen`实现`hmbs_tmpfile()`；shim需`_POSIX_C_SOURCE`声明mkstemp，TMPDIR缺失时回落到当前可写目录而非/tmp
2. 同文件`_link_test`仅对munit目标加`-Dtmpfile=hmbs_tmpfile`并链接该对象：`cc ... opaque-munit_0.o opaque-munit_1.o hmbs_tmpfile_shim.o ...`；库源码与归档产物不动，不用LD_PRELOAD；同时`_cflags`增加`-Dexpand_message_xmd=oprf_expand_message_xmd`别名兼容liboprf更名，不改上游源码、不降级liboprf
3. `archives/l/libopaque/1.0.1/notes.md`新增记录：tmpfile重定向兼容点与更名证据与别名方案（第6条）
4. 验证：`./opaque-test && ./opaque-munit --fatal-failures`，真机`HMBS_UPSTREAM_TEST_RESULT`显示33/33通过（discovered 33 executed 33 passed 33 failed 0 skipped 0）；门禁由`v2:upstream_test:test_assertion_failed`转为`v2:compile:temporary_directory_readonly`最终passed
## 禁止策略
- 禁止仅跑1个end-to-end而丢弃32个munit矩阵用例后标记通过（`HMBS_UPSTREAM_TEST_RESULT={..."discovered":1..."status":"passed"}`）；门禁要求保持33全量，必须真实发现并执行；违例致evidence incomplete退回修复循环
- 禁止减少用例计数、跳过失败用例或改库代码绕过tmpfile；仅重定向测试harness的tmpfile调用
## 与相近条目的边界（查重）
- 查重对tmpfile shim与liboprf更名别名零覆盖：增量性成立
- 既有readonly_tmp条目仅处理mktemp/getcwd/guard页/umask场景，不覆盖munit经tmpfile缓冲stderr本场景
- 类别性成立：TMPDIR感知的hmbs_tmpfile shim与vendored依赖前缀更名-D别名均为跨库可复用模式，且33/33通过验证，非临时补丁
## 适用判断
- 适用：上游测试框架经tmpfile()/tmpfile_s()缓冲输出且真机/tmp只读报EACCES/Permission denied(13)时；上游库调用的依赖符号在新版依赖中仅加前缀更名且签名一致、vendoring新版依赖而不改上游源码时可复用-D别名
- 不适用：库运行时自身依赖/tmp可写、或失败非Permission denied/EACCES时勿套用
- 注意：需先核对更名前后签名完全一致，不可盲目别名，仅处理已确认更名符号；shim仅用于测试目标，需_POSIX声明与可写目录回退
