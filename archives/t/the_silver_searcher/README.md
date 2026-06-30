# the_silver_searcher (ag)

## 简介
the_silver_searcher（ag）是一个类似于 ack 的代码搜索工具，但速度更快。它使用 PCRE 正则表达式库，支持多种搜索选项。

## OHOS 适配
- 需修复 zfile.c 条件编译结构错误（源码 bug）
- 需修改 configure 中的 umask 077→022（E011 平台适配）
- 需禁用 lzma 支持（缺少依赖）
- 需使用 autoreconf -i 生成 configure（原始源码包缺少）
- 使用 -fcommon 解决 duplicate symbol 问题

## 依赖
- pcre（必需，PCRE 正则表达式库）

## 功能验证
```bash
ag --version
ag "pattern" /path/to/search
```

## 功能限制
- 当前版本不支持压缩文件搜索（xz/lzma/gzip）
- 基本搜索功能正常
- PCRE JIT 加速正常
- zlib 支持正常

## 参考
- GitHub: https://github.com/ggreer/the_silver_searcher
- 官方文档: https://geoff.greer.fm/ag/