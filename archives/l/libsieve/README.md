# libsieve

## 简介
Sieve 邮件过滤语言（RFC 3028 及其扩展）的独立解析与执行库，
源自 Cyrus 邮件系统的 Sieve 实现，对外提供 `sieve2_*` 公共 API
（头文件 `sieve2.h` / `sieve2_error.h`，库文件 `libsieve`）。

## OHOS 适配
- 构建入口在 `src/` 子目录（顶层 Makefile 只做 release 打包），
  配方用 `autotools.configure(build_script_folder="src")`
- 2007 版 `config.sub` 不认识 aarch64，用
  `patches/0001-src-config.sub.patch` 补齐（POSIX 兼容改法）
- 上游 `make check` 为空；真实套件是 `sv_test/testcomp` +
  `testvalid.sh`(12) + `testmessage.sh`(24)，共 37 项，
  在配方 `build()` 中逐项运行并计数

## 依赖
- 无

## 功能验证
```bash
# test_package 正向用例：validate + execute 一条 keep/discard 脚本
# test_package 反向用例：破损脚本必须被拒绝
```

## 参考
- 官网: http://libsieve.sourceforge.net/
- 上游代码: https://github.com/sodabrew/libsieve
