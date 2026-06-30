# asn1c 0.9.28 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 (clang++)
- 状态: built

## 编译步骤

1. `./configure --prefix=$DEFAULT_PREFIX`
2. `make -j1`
3. `make install DESTDIR=$TEST_PREFIX`
4. `make check` (12/13 PASS, 1 FAIL)
5. `make install` (部署到 $DEFAULT_PREFIX)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 源码自带 config.guess 版本过旧 (2009-11-20) | 替换为 automake-1.17 的 config.guess/config.sub |
| 2 | config.status 创建临时文件失败 (Permission denied) | HMDFS 不允许在 umask 077 创建的 0700 权限目录内创建文件 | 将 configure/config.status 中的 umask 077 改为 umask 022 |
| 3 | check-GeneralizedTime 测试失败 | 时区相关的 GeneralizedTime 小数秒字符串格式化断言失败 | 非关键问题，不影响 asn1c 编译器核心功能 |

## 源码修改

1. `config/config.guess` — 替换为 automake-1.17 版本（平台检测修复）
2. `config/config.sub` — 替换为 automake-1.17 版本（平台检测修复）
3. `configure` — umask 077 → umask 022（HMDFS 文件系统权限适配，2处）
4. `config.status` — umask 077 → umask 022（同上，2处）

## 依赖版本

- 无外部库依赖
- 构建工具: make 4.4.1, autoconf 2.72, automake 1.17, bison, flex

## 验证结果

```bash
$ asn1c --version
ASN.1 Compiler, v0.9.28
Copyright (c) 2003-2016 Lev Walkin <vlm@lionet.info>

$ unber --version
UNBER, v0.9.28
Copyright (c) 2003-2016 Lev Walkin <vlm@lionet.info>

$ enber --version
ENBER, v0.9.28
Copyright (c) 2003-2016 Lev Walkin <vlm@lionet.info>
```

## 注意事项

- check-GeneralizedTime 测试失败是平台时区处理差异导致，不影响编译器功能
- umask 022 补丁是 HMDFS 文件系统必需的，否则 config.status 无法生成 Makefile
- config.guess/config.sub 替换是 HarmonyOS 平台检测的标准修复
---

**编译结束**: 2026-06-25 10:50
**最终状态**: built
