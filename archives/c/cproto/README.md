# cproto

C 函数原型生成工具 — 从 C 源文件提取函数声明，生成 ANSI 或 K&R 风格的原型声明。

## 版本列表

| 版本 | 状态 | 日期 |
|------|------|------|
| 4.7y | 已发布 (published) | 2026-06-11 |

## 简介

cproto 是一款读取 C 源文件并生成函数原型声明声明的工具。它可以输出 ANSI C 风格、传统 K&R 风格或两者兼有的原型。同时还支持生成 lint 库声明。

典型用法：
```bash
# 从函数定义生成 ANSI 原型
cproto -a file.c

# 查看版本
cproto -V
```

## 鸿蒙平台适配说明

- 需要 E007 补丁：修改 config.guess/config.sub 以识别 HarmonyOS 系统（三元组 `aarch64-unknown-linux-ohos`）
- 需要 E002 适配：禁用 `HAVE_TMPFILE`（系统 tmpfile() 在 HMDFS 上因 /tmp 只读而失败），改用 cproto 自带实现（依赖 `$TMPDIR`）
- HMDFS 限制：config.status 的 `umask 077` 导致临时子目录不可写，需移除 umask 并添加 chmod
- 版本查看使用 `-V` 参数（不支持 `--version`）
- 运行时需设置 `TMPDIR` 环境变量（避免 tmpfile() 写入只读的 /tmp）