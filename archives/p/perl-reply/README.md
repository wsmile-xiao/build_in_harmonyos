# Reply

Perl 交互式 REPL (Read-Eval-Print Loop) 工具，提供即时 Perl 代码求值环境。

## 编译指导

在 HarmonyOS/OHOS 平台编译时需注意：

- 纯 Perl 模块，使用 ExtUtils::MakeMaker (Makefile.PL) 构建系统
- OHOS SELinux 限制 .so 加载，XS 模块 (PadWalker, Devel::LexAlias, PerlIO::utf8_strict) 无法使用
- Conan 配方已 bundle 15 个纯 Perl 依赖模块到 lib/perl5
- reply 脚本已修补为自定位 lib 目录 + 强制纯 Perl 模式 (PERL_PARAMS_UTIL_PP=1, PACKAGE_STASH_IMPLEMENTATION=PP)
- 需移除默认配置中依赖 XS 的插件: LexicalPersistence, ReadLine, FancyPrompt

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [0.42](./0.42/) | published | 2026-06-29 |
