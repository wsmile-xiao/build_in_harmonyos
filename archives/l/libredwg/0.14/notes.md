# libredwg 0.14 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang/clang++
- 状态: built

## 编译步骤

Autotools原生构建：AutotoolsToolchain生成工具链后configure+make -j1+make check+make install。configure参数：--enable-static --disable-shared --disable-bindings --disable-docs --disable-python --disable-werror --build=aarch64-unknown-linux-gnu。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | archive目录缺失导致真机预检incomplete | 任务目录下无archives/l/libredwg/0.14，hmbs无法读取代码树 | 新建完整配方树（conanfile/conandata/manifest/notes/test_package/commands.json） |
| 2 | config.guess不识别OHOS | 上游config脚本过旧 | --build=aarch64-unknown-linux-gnu强制三元组（同bash/5.3做法） |
| 3 | docs/bindings需缺失依赖 | texinfo/SWIG/python头在CI缺失 | --disable-bindings --disable-docs --disable-python |
| 4 | 新版clang警告被当错误 | 上游默认--enable-werror | --disable-werror |
| 5 | 真机configure止于config.status "confXXXXXX/subs1.awk: Permission denied" | autoconf以`umask 077 && mktemp/mkdir ./confXXXXXX`建临时目录，HMDFS上0700目录不可写（E011） | build()内原地将configure中`umask 077`替换为`umask 022`后再configure（同lame/3.100、libarchive/3.8.7做法，不新增补丁文件） |
| 6 | 真机package止于`install -c .libs/libredwg.a`后`chmod: cannot access .../lib/libredwg.a: No such file` | 真机HMBS能力hardlink=0/chmod=0，host install垫片无法落盘libtool产物（install看似成功但文件缺失，随后chmod失败） | package() walk源码/构建目录定位自带install-sh，改走`make install -j1 INSTALL="/bin/sh install-sh -c" INSTALL_PROGRAM/DATA/SCRIPT同值 MKDIR_P="/bin/sh install-sh -c -d"`并附可写TMPDIR，找不到时回退默认安装 |
| 7 | 真机package止于`copy() got an unexpected keyword argument 'delete'` | conan.tools.files.copy无delete参数（conan 2.30），删.la应走rm | 改用`rm(self, "*.la", package_folder/lib)`并补rm导入 |
| 8 | 真机test_package止于`dwgread: inaccessible or not found`（exit 127） | `make install`装好了share/但bin/dwgread缺失（libtool程序安装经install垫片在hardlink=0/chmod=0下落盘失败）；且test_package只靠PATH裸调`dwgread` | package()在install后回退：build树programs[.libs]/下找ELF真二进制拷入package bin并补755（跳过libtool wrapper脚本）；test_package改走package绝对路径+PATH双检，缺文件直接报错不静默跳过 |
| 9 | 真机诊断上游测试发现0/无HMBS标记 | build()只跑`make check`不输出机器证据标记 | build()新增解析test-suite.log（TOTAL/PASS/FAIL/SKIP/ERROR，无summary时回退数PASS:/FAIL:行）并输出HMBS_UPSTREAM_TEST_RESULT；test_package输出HMBS_TEST_PACKAGE_RESULT（5 lib断言+1 CLI=6） |
| 10 | 真机`make check -j1`链接期`libtool: fork: Out of memory`（multileader/object_ptr等，Error 254） | 测试二进制以clang -O3逐个编译+链接libredwg.la，单测内存峰值超真机限额；-j1串行仍超限 | 保持全量套件不跳过：库仍以默认优化`make -j1`构建，仅`make check`阶段覆盖`CFLAGS=-O1 -g0 -DNDEBUG`降低测试编译/链接峰值；另加`--disable-dependency-tracking`削减.deps IO开销 |

| 11 | `make check` directly fails with make usage text (`--warn-undefined-variables ... This program built for aarch64`) + Error 2 | `CFLAGS=-O1 -g0 -DNDEBUG` passed as bare make arg splits at spaces; `-g0` parsed as unknown make option | Quote whole value as single shell token `CFLAGS="-O1 -g0 -DNDEBUG"` + pass `TMPDIR=<writable>` as make var (ndiff precedent); keep full suite, no skipping |
| 12 | `make check` exits 0 but no test-suite.log (marker total=0, preflight upstream_test failed) | Top-level `TESTS` gated on `HAVE_SHELLCHECK` (Makefile.am: `TESTS =` + `if HAVE_SHELLCHECK TESTS += log dwg dxf ...`); device has no shellcheck so top-level suite empty by design. Real suites live in test/unit-testing (~200 check_PROGRAMS) + programs/ (alive/dxf/dxfb.test) | build() keeps single-token `CFLAGS=-O1` (no spaces/quoting pitfalls, asserts stay enabled: drop `-DNDEBUG` which would fake passes), then if no logs found explicitly `make -C test/unit-testing check` + `make -C programs check`; marker refactor `_scan_roots/_find_upstream_logs` shared by build fallback and emit |
| 13 | Same fingerprint again (conditional `make -C` fallback still zero logs) | Conditional gate itself suspect (log discovery may miss, or subdir paths differ); `make -C` flag ordering unverified | UNCONDITIONAL explicit suites: top-level `make check` stays, then always `make check` with cwd=test/unit-testing and cwd=programs via self.run(cwd=...), with self.output.info dir-layout diagnostics; marker command updated to truthful string |
| 14 | Same fingerprint 3rd time (unconditional subdir runs exit 0 yet scan still finds zero logs) | File discovery untrustworthy in this env (scan misses logs that must exist); evidence source must change, not the invocation | Two subdir suites become the ONLY upstream execution (drop empty top-level check); each stdout captured to hmbs-check-*.log and tail echoed to build log; marker parses captured framework text per-suite (log wins when present, no double count); missing subdir raises instead of silent zero; helpers `_counts_from_text/_counts_from_result_lines/_info_captured_tail` |
| 15 | 预检test_package通过但判incomplete缺HMBS_UPSTREAM_TEST_RESULT（本轮） | build()内标记只走self.output.info单通道且仅在构建时输出；包缓存命中时build()被跳过，test_package日志无上游标记穿透缓存；另零log时无兜底计数 | 双通道+持久化重发表（dd-opentracing-cpp经验适配）：build标记改print+info双通道并落盘build/hmbs-upstream-result.json，package()转存入share/libredwg，test_package/test()重读重发表真实计数；零log时加直接执行已构建unit-testing ELF二进制兜底（exit 0计通过，非零计失败，无跳过伪造） |

## 源码修改

无补丁，纯configure参数适配。

## 依赖版本

无运行时依赖；构建仅需系统autotools/clang。out_dxf等模块默认开启，需libm（system_libs声明m）。

## 验证结果

待真机预检：conan create应依次通过编译、make check（unit-testing数百用例+programs alive/dxf/dxfb+顶层集成套件，build输出HMBS_UPSTREAM_TEST_RESULT）与test_package（test_libredwg 5断言+dwgread --version双检，输出HMBS_TEST_PACKAGE_RESULT discovered=6）。package对bin/lib ELF做best-effort self-sign（gdk-pixbuf先例，env=None，缺signer时跳过）。

## 注意事项

- 上游测试量大，CI超时预算可能需上调；缺jq/jing时对应json/svg子项自动跳过，不视为失败。
- 产物含bin（dwgread/dwgwrite/dwg2dxf等），须配commands.json，PR正文按真机日志如实回填通过率。
