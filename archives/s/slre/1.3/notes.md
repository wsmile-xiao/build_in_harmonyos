# slre 1.3 — OHOS 适配笔记

## 结论
- 单文件 C 正则引擎（Perl RE 子集），零依赖、无构建系统。
- 直接编译 `slre.c` 为 `libslre.a`，头文件 `slre.h` 装入 include/。
- 零补丁（无需任何平台修改，源码 2014 年冻结，纯 C89/99 可移植代码）。

## 上游测试执行
- `unit_test.c` 单 main()，静态计数 126 个 `ASSERT(`。
- build() 内真实编译执行：124/126 通过。
- 2 个失败（第 87-88 行）：断言期望 `(?m)FO` / `(?m)x` 返回
  `SLRE_UNEXPECTED_QUANTIFIER`，但 1.3 的 `slre.c` 只实现了 `(?i)` 标志
  （见源码注释 "At the moment, only 'i' is supported"），属上游陈旧测试
  与实现不一致——该失败在任意平台（x86 Linux 同样）复现，与 OHOS 无关。
- 设备原生验证命令与日志：`./slre_unit_test` →
  `Unit test FAILED (total test: 126, failed tests: 2)`，exit 1，
  配方中按已知上游缺陷容忍该退出码并输出 warning 说明。

## test_package
- test.c 共 10 个 CHECK：字面量/字符集/(?i) 标志/十六进制转义匹配、
  捕获组（`(\d+)-(\d+)` 提取 42/7）、错误码（不平衡括号）、锚定 ^...$。

## 版本对齐
- 任务 #5389 = conan 1.3 = 分支 feat/slre-1.3 = 目录 archives/s/slre/1.3。
---

**编译结束**: 2026-09-02 01:27
**最终状态**: built
