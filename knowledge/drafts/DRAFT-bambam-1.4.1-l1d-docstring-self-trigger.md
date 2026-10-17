# DRAFT-bambam-1.4.1-l1d-docstring-self-trigger — CI L1d "fake test" 误报：文档注释里描述规则本身触发子串匹配

> **Contributor**: bambam-1.4.1 | **Status**: DRAFT | **Updated**: 2026-10-04
> **Severity**: medium | **Category**: ci / test / false-positive / python
> **Audience**: 所有在 test_package/conanfile.py 中为真实测试写注释/文档字符串的库

## 问题（真实首错）

bambam/1.4.1 test_package/conanfile.py 的 docstring 里写了：
"CI L1d 启发式对 self.run 行做 (echo|print|true) 子串匹配，故命令行不使用这三个字面量"。
该注释行同时含 `self.run` 与 `(echo|print|true)`，而 L1d 用
`grep -qE "self\.run.*(echo|print|true)" test_package/conanfile.py` 做**逐行**
子串匹配——注释/文档行同样被检查 → 命中 → W3 L1d 误判 `fake test detected`。

测试本身 100% 真实（`bin/bambam --help` + SDL dummy 冒烟 + 上游 unittest 4/4）。

## 根因

L1d 启发式（`build_and_test.sh`）为行内子串匹配且不区分注释/代码：
`self.run` 之后同一行内出现 `echo`/`print`/`true` 任一子串即判 fail。
因此"在 conanfile.py 里描述 L1d 规则"这一行为本身就会触发检测器。

## 解决方案

1. **执行端（推荐）**：不要在 test_package/conanfile.py 的注释/文档里同时出现
   `self.run` 与 `(echo|print|true)` 于同一行；需提示时改写为不含该模式的描述
   （如"本 test() 全部为真实执行，不使用空壳 shell 命令"）。改完重跑 W3/L1d。
2. **CI 维护端（根治）**：L1d 改为词边界/独立词匹配并跳过注释行，或判 fail 前
   校验 test() 是否引用包内构建/运行目标（有真实执行证据时豁免）。

## 验证

- bambam/1.4.1：删除 docstring 中 "self.run ... (echo|print|true)" 注释行后
  `grep -nE "self\.run.*(echo|print|true)"` 输出 CLEAN，conan create（含
  test_package 三连真测试）exit 0。

## 适用边界

- ✅ 适用：test_package/conanfile.py 注释或文档字符串同时含 `self.run` 与
  `echo`/`print`/`true` 字面量，且测试本身真实。
- ❌ 不适用：test() 真的只有 echo/print（真 fake test，应按 L1d 原意修复）。
- ⚠️ 与 `DRAFT-ci-l1d-print-substring-false-positive` 同源不同触发点：
  前者是消费者可执行文件名含 print 子串；本条是注释记录规则本身。
