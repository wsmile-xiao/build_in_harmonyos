# cliquer 1.21 适配笔记（HarmonyOS PC · autotools）

## 定位
- 产出 libcliquer.so / libcliquer.a（图最大团/clique 枚举 C 库）与 CLI 工具 cl。
- 配方以已合入的 cliquer/1.23 配方为底稿（recipe-search top1，score=0.5），仅版本/源 URL/SHA256 差异。

## 源
- 官方 tag v1.21（dimpase/autocliquer，上游维护分支；v1.21 无 release 资产，用官方 GitHub archive URL）
- https://github.com/dimpase/autocliquer/archive/refs/tags/v1.21.tar.gz
- sha256: 297de57628cf0d89093ef6d3b366a1594b180970e5ffee1395b2b305859584e6

## W0/W0b
- preflight_check.sh：无依赖声明，通过。
- 历史归档 archives/c/cliquer/1.23/notes.md 已读：其 umask 修复、ELF 重签、删 .la 结论全部继承到本配方。
- lang-preflight：task=cpp，detected=c（c↔cpp 兼容族），源文件 c:5 占比 100%，通过。

## 探索构建（真机 /storage/Users/currentUser/builds/cliquer-1.21.work）
1. release/GitHub archive 无 configure → `autoreconf -fi` 自举（autoconf 2.73 / automake 1.18.1）。
2. config.guess 不识别 HongMeng 内核（"cannot guess build type"）→
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`。
3. 设 --host 后 configure 探测到 aarch64-unknown-linux-ohos-clang 包装器但无法创建可执行文件
   （explore2.log：C compiler cannot create executables）→ 显式 `CC=clang CXX=clang++`。
4. config.status 报 `can't create ./confR07vkg/subs1.awk: Permission denied`（E011/E114，HMDFS umask 077）→
   受控修复 `sed -i 's/umask 077/umask 022/g' configure` 后重跑，通过。
5. make -j1 / make install DESTDIR 均通过；产物 libcliquer.so.1.0.21、libcliquer.a、bin/cl。
6. 配方内建同等修复（1.23 配方原生含）：autoreconf 自举判定、umask 修补置于 autoreconf 之后、
   package() 删 .la、OHOS 下 ELF 自签（_sign_binaries）。

## 上游测试四维账本（R51/R52 口径）
- N_static（原子检查）：20 —— test/testcases.c main() 逐条计数：
  test_single_clique ×4（L174/177/180/183）、test_all_cliques ×5（L188/191/194/197/200）、
  test_max_weight ×2（L205/208）、test_user_function ×1（L213）、test_too_small_array ×1（L216）、
  test_single_w_clique ×3（L220/223/226）、test_all_w_cliques ×3（L229/232/235）、
  test_reentrance ×1（L239）。
- N_registered（automake 注册）：1 —— test/Makefile.am `TESTS = testcases`（check_PROGRAMS=testcases，
  链接 ../lib/libcliquer.la；20 个原子检查在同一程序内，任一断言失败即非零退出）。
- N_executed：1/1 PASS —— 真机 `make check`：
  Testsuite summary for cliquer 1.21: TOTAL 1 / PASS 1 / SKIP 0 / FAIL 0 / XPASS 0 / ERROR 0
  （即 20 个原子检查全部执行且通过；test-suite.log 同口径）。
- N_consumer（新增消费者测试）：1 —— test_package/test.c，真实 API 计算断言 ×3
  （graph_new 非空、K4 最大团=4、删边(0,1)后最大团=3），编译并链接 libcliquer 实际调用。

## 状态
built —— conan create 真机验证通过后回填（见 .ci-result.json / reports/）。
---

**编译结束**: 2026-09-08 23:43
**最终状态**: built
