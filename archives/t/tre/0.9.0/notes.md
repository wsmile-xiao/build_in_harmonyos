# TRE 0.9.0 鸿蒙 PC 适配 (v8.7 Conan)

## 当前状态 (2026-07-28)
- conan create: PASS (100% tests passed)
- make check: 3/4 suites passed (wretest 4/53447 locale 限制)
- 源码: GitHub release (含预生成 configure，无需 autoreconf)
- 补丁: 2 个 (0001-config.sub + 0002-configure)

## v7.8 → v8.7 迁移说明
旧版 v7.8 (2026-05-26) 使用 laurikari.net 源码 (不含 configure，需要 autoreconf)
+ 6 个补丁。v8.7 改用 GitHub 发行版源码 (含 configure)，旧补丁中的
configure.ac/Makefile.am/Makefile.in/config.h.in/configure~ 均不适用于新源码。
仅保留并重新生成 config.sub 补丁 (E007) 和 configure 补丁 (E097)。

## 历史记录 (v7.8, 2026-05-26)
tre 0.9.0 曾在 v7.8 框架下编译通过 (laurikari.net + autoreconf + 6 补丁):
- make check: agrep/retest/test-str-source 通过, wretest 4/53447 失败
- agrep 验证: 8/8 通过
- libtre API 验证: 4/4 通过
