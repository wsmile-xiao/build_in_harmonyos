# omega/2.0.0 测试报告

- 日期: 2026-09-10/11（UTC+8 跨零点上连续执行）
- 平台: OpenHarmony PC (HarmonyOS, HongMeng Kernel 1.12.0, aarch64)
- 工具链: clang 15.0.4 / LLVM, libc++, musl (`/lib/ld-musl-aarch64.so.1`)
- 上游: xapian-omega 2.0.0（GNU Automake 测试 harness，`make check`）

## 1. 上游自动化测试（真实执行，非 test_package 替代）

### 1.1 测试入口核验

`Makefile.am:176-192`：`check_PROGRAMS` 10 个（其中 8 个注册为 TESTS，`omindexcheck`/`timecheck` 为其他用例的内部辅助程序，不单独注册）；`dist_check_SCRIPTS` 3 个；`TESTS` 注册表共 **11 项**。`PL_LOG_COMPILER = $(PERL)`（omegatest.pl 经设备 perl 5.42 执行）。

### 1.2 探索阶段真机全量执行（automake serial）

- 命令: `MAGIC=<libmagic>/share/misc/magic.mgc LD_LIBRARY_PATH=<xapian-core>/lib:<zlib>/lib make check`
- 日志: `/storage/Users/currentUser/tttt/omega-2.0.0-adapt/logs/explore-makecheck-final-2026-09-10-2344.log`
- 明细: `/storage/Users/currentUser/tmp/builds/omega-2.0.0.work/test-suite.log` 及同名 `*.log`
- 结果: **TOTAL 11 / PASS 11 / SKIP 0 / FAIL 0 / XFAIL 0 / ERROR 0**（rc=0）

| # | 用例 | 类型 | 结果 | 单项日志 |
|---|------|------|------|----------|
| 1 | atomparsertest | C++ 单测 | PASS | omega-2.0.0.work/atomparsertest.log |
| 2 | csvesctest | C++ 单测 | PASS | omega-2.0.0.work/csvesctest.log |
| 3 | htmlparsertest | C++ 单测 | PASS | omega-2.0.0.work/htmlparsertest.log |
| 4 | jsonesctest | C++ 单测 | PASS | omega-2.0.0.work/jsonesctest.log |
| 5 | md5test | C++ 单测 | PASS | omega-2.0.0.work/md5test.log |
| 6 | omegatest.pl | perl 集成套件（数百内部断言；faketime 缺失时内部用例自跳过，脚本自带保护） | PASS | omega-2.0.0.work/omegatest.log |
| 7 | omindextest | shell 集成（需 MAGIC，见 §1.4） | PASS | omega-2.0.0.work/omindextest.log |
| 8 | sdbntest | C++ 单测 | PASS | omega-2.0.0.work/sdbntest.log |
| 9 | sourcetest | shell 源码卫生检查 | PASS | omega-2.0.0.work/sourcetest.log |
| 10 | urlenctest | C++ 单测 | PASS | omega-2.0.0.work/urlenctest.log |
| 11 | utf8converttest | C++ 单测 | PASS | omega-2.0.0.work/utf8converttest.log |

### 1.3 conan create 内复跑（配方 build() 集成，CI 同路径）

- W3 本地 CI 模拟（CI 同源 setup.sh + build_and_test.sh）: `archives/o/omega/2.0.0/reports/w3-local-ci.log` L646 `RUN: make check -j1` → L680-684 **TOTAL: 11 / PASS: 11 / SKIP: 0 / FAIL: 0**，L833 `Created package revision f69fa218…`；`.ci-result.json exit_code=0`（log_sha256 `a4be423d…f51a`，实测 sha256sum 一致）
- 提交前复核（2026-09-11 删除本地二进制后强制全新重编）: `~/tttt/omega-2.0.0-adapt/logs/recheck-create-fresh-2026-09-11-1336.log` L558 `RUN: make check -j1` → L680-685 **TOTAL: 11 / PASS: 11 / SKIP: 0 / FAIL: 0**，L749 同一 package revision `f69fa218…`（确定性构建）
- 注: `reports/conan-create.log` 当前保存的是二次验证运行（配方 rev 未变、conan 复用包并仅复跑 test_package，尾行 `omega smoke OK`）；完整构建链证据以上述 W3 与 recheck 日志为准

### 1.4 环境适配说明（非代码缺陷）

1. 首轮 `make check`（未注入 MAGIC 时）为 10 PASS / 1 FAIL（omindextest）：静态 libmagic 在 OHOS 无默认 magic.mgc 搜索路径。注入 `MAGIC` 后转 PASS。配方已在 `Environment(scope=build)` 中固化该变量，后续所有执行均 11/11。
2. 上游测试对 faketime（可选工具，本环境无）的处理是脚本内置跳过，不计 SKIP——automake 视角注册用例整体 PASS。

## 2. test_package（消费者视角，L1）

- 命令: `bash smoke.sh`（conan create 的 Launching test_package 阶段，`env="conanrun"`）
- 内容: 3 个 CLI `--version` 断言 + scriptindex 建库 + omega CGI `P=quick brown fox` 查询命中断言
- 输出: `omega smoke OK`（conan-create.log L789、w3-local-ci.log）
- test_package **不替代** §1 上游测试统计。

## 3. 功能冒烟补充（探索阶段）

- `file omega` → ELF 64-bit LSB arm64, dynamic（musl），真机 rc=0 可执行
- `omega 'P=quick brown fox'` → `Query((Zquick@1 AND Zbrown@2 AND Zfox@3))`
- `make install DESTDIR=$TEST_PREFIX` rc=0，产物见 `.staging-verified`（staging 验证通过）

## 4. 失败与修复统计

| 现象 | 根因 | 修复 | 复验 |
|---|---|---|---|
| configure `cannot guess build type` | config.guess 不识别 HarmonyOS | 补丁 0001/0002 | configure rc=0 |
| `xapian.h` 找不到 / `-I//include` | 已发布 xapian-core 包内 xapian-config prefix="/" | 配方生成私有修正副本注入 XAPIAN_CONFIG | make rc=0 |
| omindextest FAIL | 静态 libmagic 缺 magic.mgc 路径 | MAGIC 环境变量注入 | 11/11 PASS |
| G0 clean-verify configure 中止 | HMDFS getcwd 不支持（已知平台限制，补丁可应用性已由 G0 前半程验证：3/3 applies） | 不修复（非阻塞；W3/conan create 为权威门禁） | W3 PASS |
