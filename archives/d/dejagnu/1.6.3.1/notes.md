# dejagnu 1.6.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
2. Recipe applies 0004-configure.patch (E011 umask 077 to 022 fix for HMDFS)
3. configure then make -j1 then make install
4. make check runs dejagnu own testsuite via runtest

## 遇到的问题与解决方案

1. HMDFS umask 077 creates restricted temp dirs - root cause E011 HMDFS setgid plus umask - fix 0004-configure.patch umask 077 to 022
2. config.guess fails on OHOS - root cause old config.guess does not recognize OHOS - fix pass build/host via RUNTESTFLAGS

## 源码修改

- patches/0004-configure.patch: configure script umask 077 to 022 (E011 fix)

## 依赖版本

- expect 5.45.4 (runtime: runtest needs expect interpreter)
- tcl 8.6.14 (transitive via expect)
- zlib 1.3.1 (transitive via expect)

## 验证结果

make check runs runtest on dejagnu own testsuite
Results: launcher 54 pass, libdejagnu 5 pass, runtest 48 pass plus 1 unresolved
report-card 2 unresolved (expect spawn issue on OHOS)

## 注意事项

- dejagnu main output is Tcl scripts (runtest, dejagnu), not ELF binary
- make check needs expect available, recipe declares requires expect 5.45.4
- report-card testsuite has expect spawn issue (OHOS PTY/expect braced-form bug)

---

**编译结束**: 2026-08-19
**最终状态**: built

## 补丁处理说明（round-8，用户决定：只做新增，不删除）

- 0001-Makefile.patch / 0002-config.log.patch / 0003-config.status.patch 为基线遗留的
  configure 生成产物快照（Makefile / config.log / config.status），未被 conandata.yml
  引用、不会被应用；按用户决定「如果可以只做新增，不删除」**保留不删除**。
- 0004-configure.patch 为唯一真实源码修复（E011 umask 077→022），conandata.yml 仅
  引用该 patch 并应用。
- 随 PR 交付的 3 条知识草稿（路径 B【知识库扩展】，knowledge/drafts/，各 .kv + .md）：
  1. DRAFT-dejagnu-runtest-ohos-test-runtime —— build() 集成 make check 的
     runtest 运行时注入 + RUNTESTFLAGS 动态三元组（含 E011 边界）
  2. DRAFT-ohos-test-package-tcl-direct-require —— test_package 直连 tcl +
     TCL_LIBRARY + bash 替代 mksh
  3. DRAFT-jc6-origin-main-stale-ref —— JC6 门禁 origin/main 过时引用陷阱
