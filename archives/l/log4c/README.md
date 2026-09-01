# log4c

## 简介
C 语言的日志库，仿 log4j 模式（category / appender / layout），LGPL-2.1。

## OHOS 适配
- autotools：config.sub 不认 aarch64-linux-ohos → configure 覆盖 --host/--build 为 gnu 三元组(原生 build==host)
- uname-shim 修 config.guess（设备 uname=HarmonyOS）
- configure 内 `umask 077` → `umask 022`（HMDFS 上 config.status 临时文件权限问题，同 lame 3.100）
- `--enable-test` 打开 tests/ 子目录，`make check` 真实执行上游官方测试（CI L1）

## 依赖
- 无 conan 依赖（expat 默认关闭，用内置 yacc/lex 解析配置）
- 编译工具: clang, autotools

## 上游测试
`make check`（tests/log4c/check-local）：test_category / test_layout_r / test_rc / test_big
共 16 个用例，与 .ref 基准 diff。实测 Total 16 / Pass 16 / Fail 0 / Skip 0。

## 参考
- 官网: https://log4c.sourceforge.io/
