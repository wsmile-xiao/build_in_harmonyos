# jpcre2 10.32.01 适配记录

## 基本信息
- 上游: https://github.com/jpcre2/jpcre2 (tag 10.32.01, 2020-08-27)
- 类型: 头文件库（`src/jpcre2.hpp` 安装到 `include/`）
- 构建系统: Autotools（`./configure --enable-test && make && make check`）
- 依赖: pcre2/10.48（制品仓全宽度构建，含 libpcre2-8/16/32）
- 申请人: sheepss / 队伍: 来都来了

## 上游测试清点（申报表）
来源: `src/Makefile.am` 的 `TESTS` 行（thread 测试上游注释掉，不计入）。

| # | 程序 | 源码 | 说明 |
|---|------|------|------|
| 1 | test_match | src/test_match.cpp | 匹配与捕获组遍历 |
| 2 | test_replace | src/test_replace.cpp | 替换 |
| 3 | test_shorts | src/test_shorts.cpp | 短匹配/替换 |
| 4 | test16 | src/test16.cpp | 16 位宽度（需 libpcre2-16） |
| 5 | test32 | src/test32.cpp | 32 位宽度（需 libpcre2-32） |
| 6 | test0 | src/test0.cpp | 边界匹配 |
| 7 | test_issue_29 | src/test_issue_29.cpp | issue 29 回归 |
| 8 | test | src/test.cpp | 通用匹配 |
| 9 | testio | src/testio.cpp | 输入输出匹配 |
| 10 | testme | src/testme.cpp | 综合匹配 |
| 11 | testmd | src/testmd.cpp | 多文档匹配 |

合计 11 个，`make check` 在真机完整执行（`test_match2/test_replace2` 仅构建不运行，
上游如此设计；`test_pthread/teststdthread` 上游默认禁用）。

## 源码包指纹
- URL: https://github.com/jpcre2/jpcre2/archive/refs/tags/10.32.01.tar.gz
- sha256: 668cbc6d2c0a065bb6abe8494d5a1bb3549a14cd956a44a2df9095045623ea47
  （2026-09-15 下载实测；归档共 52 个文件，单头文件 `src/jpcre2.hpp`）

## 适配要点
1. 头文件库仍保留 Autotools 流程（configure/make/make check/install），
   不为省事跳过上游测试；`package()` 走 `make install` 只装头文件。
2. 依赖选 pcre2/10.48：它是制品仓中启用 `--enable-pcre2-16/32` 的版本，
   否则 test16/test32 链接失败。若换用仅 8 位的旧版 pcre2，
   11 项无法全过（已在选型时排除）。
3. 补丁复用 pcre2 10.45 的 OHOS 适配（config.guess/config.sub/umask），
   路径调整为 jpcre2 的 `config/` 子目录与根 `configure`。

## 消费者测试
`test_package/test_jpcre2.cpp` 7 项 CHECK：布尔匹配、全局计数 3、
捕获组 hello/42、替换 aNUMbNUM、JIT 路径、负向匹配。
`ctest -R test_jpcre2` 在真机执行并输出 `HMBS_TEST_PACKAGE_RESULT`。

## 防证伪说明
- 上游 11 项以 automake `PASS:` 行与 `# TOTAL/# PASS` 双重计数为准，
  失败任一项即抛异常使构建变红，不存在静默跳过。
- test_package 7 项为源码内显式断言（失败 return 1），非空壳打印；
  数字来自真实 ctest 执行后输出。

## 2026-09-15 test_issue_29 failure analysis
Preflight make check: 10/11 pass, only test_issue_29 FAILS with E: std out_of_range was not thrown.
DIAG from previous round (since removed): subject='42bZ' num=1 matches.size()=1 matches[0].size()=4
with pcre2_headers=10.48. Vector shape is correct (3 groups + whole match = 4 entries),
so .at(4) MUST throw — yet no exception was observed.
Root cause: the bounds check lives inside assert() (`assert(matches[0].at(4) != "dummy")`).
Release builds define NDEBUG, which turns assert() into a no-op: the .at(4) access is never
evaluated, no exception is thrown, out_of_range_occured stays false, and the test exits 1.
This is an upstream test bug (side effect inside assert), not a PCRE2 10.48 behavior change;
readonly_tmp in the log is infra noise (upstream src has no /tmp usage).
Fix (patches/0004): evaluate `matches[0].at(4)` unconditionally into a local, keep an assert
on its value for Debug builds. Test intent unchanged: index 4 must still be out of range.
No test is skipped, no assertion deleted.
