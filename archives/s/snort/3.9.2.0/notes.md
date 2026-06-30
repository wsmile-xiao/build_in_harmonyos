# snort 3.9.2.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..`
2. `make -j1`
3. `make install DESTDIR=$TEST_PREFIX`
4. 安装到 DEFAULT_PREFIX: `cp bin/snort $DEFAULT_PREFIX/bin/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接失败: undefined reference to `pdfFlexLexer::yyread` 和 `jsFlexLexer::yyread` | FlexLexer.h 声明了 `virtual int yyread(char*, size_t)` 但 flex 2.6.4 生成的扫描器代码未包含该方法的实现 | 在 pdf_tokenizer.l 和 js_tokenizer.l 末尾添加 yyread 实现，调用 LexerInput |
| 2 | staging 目录为空壳 | 首次 make 在链接阶段失败，make install 仍创建了空目录结构 | 修复链接错误后重新 make install DESTDIR |
| 3 | manifest 缺少 build_system 字段 | manifest 模板中无此字段 | 手动添加 `build_system: cmake` |

## 源码修改

- `pdf_tokenizer.l`: 末尾添加 `yyFlexLexer::yyread` 实现
- `js_tokenizer.l`: 末尾添加 `yyFlexLexer::yyread` 实现
- `0001-cmake-FindDAQ.cmake.patch`: FindDAQ.cmake 平台适配

## 依赖版本

- DAQ 3.0.27
- libpcap 1.10.5
- LuaJIT 2.1.1773724885
- LZMA 5.6.2
- OpenSSL 3.5.6
- PCRE2 10.40
- ZLIB 1.3.1

## 验证结果

```bash
$ snort --version
   ,,_     -*> Snort++ <*-
   o"  )~   Version 3.9.2.0
   ''''    By Martin Roesch & The Snort Team
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| snort-3.9.2.0-ohos-aarch64.tar.gz | 23631KB | 预编译包（含 snort, snort2lua, u2boat, u2spewfoo） |

## 注意事项

- snort --version 会输出 bootstrap dlsym 警告（snort_whitelist_append），不影响版本输出和基本功能
- FlexLexer.h 的 yyread 问题是 flex 2.6.4 与系统 FlexLexer.h 的版本不匹配导致
---

**编译结束**: 2026-06-21 16:00
**最终状态**: built
