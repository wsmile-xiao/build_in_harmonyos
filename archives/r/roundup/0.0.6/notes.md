# roundup 0.0.6 适配笔记

## 编译环境
- 构建系统: custom（纯 POSIX shell 工具，无 C/C++ 编译；上游 make = `sh -n` 语法检查 + sed 重写 shebang + chmod）
- 编译日期: 2026-09-27
- 宿主: HarmonyOS PC（aarch64），/bin/sh = MirBSD KSH R59（mksh）
- 状态: published

## 上游源码核验
- 上游: https://github.com/bmizerany/roundup（Blake Mizerany，MIT）
- v0.0.6 tarball sha256: 20741043ed5be7cbc54b1e9a7c7de122a0dacced77052e90e4ff08e41736f01c
- 源码构成: roundup.sh（9.9KB 主脚本）+ configure + Makefile + 3 个自举测试 plan；**零 C/C++ 源文件、零外部依赖**
- 上游缺陷: v0.0.6 tag 内 `ROUNDUP_VERSION` 仍为 "0.0.5"（漏更），补丁 0003 对齐

## 上游测试（R51 实测，本机 OHOS mksh 真实执行）
- 命令: `./roundup`（自举运行 4 个 *-test.sh plan）
- 结果: **18 用例 / 15 通过 / 3 失败 / 0 跳过**；exit 2 为预期（roundup-5 设计性失败驱动 roundup-1 的 `it_exits_non_zero` 断言 exit=2）
- 明细:
  - edge-test.sh: 3/3 PASS
  - ohos-test.sh（本次新增鸿蒙消费者用例）: 4/4 PASS
  - roundup-1-test.sh: 3/3 PASS
  - roundup-5-test.sh: 5 PASS / 3 FAIL —— it_fails、it_runs_after_if_a_test_fails_part_1、it_outputs_the_return_code_7 三者为上游设计性失败（plan 注释明示 "This Will Fail ... That is the point"）
- 日志: .work_scratch/roundup-final-selftest.log（work 目录实测）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 自举测试 0 用例可跑，`set: -E: unknown option` | mksh 对 `set -E`（bash errtrace 扩展）按特殊内建致命错误处理，直接终止 shell | 补丁 0003：子壳 `(set -E) 2>/dev/null` 探测，成功才在运行器设置；ERR trap（mksh/bash 均支持）保留、dash 下探测跳过 |
| 2 | it_hath_path_til_after / it_hath_not_path_before_thy 信号丢失、plan 静默消失 | mksh 无 printf 内建（bash 有）；edge plan 的 before/after 故意置空 $PATH，信号发射（外部 printf/grep）不可达致子壳死亡 | 补丁 0003：运行器启动备份 `$roundup_path_backup`，每个测试信号发射前恢复 PATH；ERR trap 体内同样恢复 |
| 3 | it_hath_not_path_before_thy 失败（PATH=空仍能找到 ls） | OHOS mksh 对空 PATH 回退默认搜索路径（bash 仅搜当前目录） | 补丁 0001：edge plan 的空 PATH 改为 PATH=/nonexistent（bash/mksh/dash 语义一致，用例意图不变） |
| 4 | PATH=/nonexistent 仍命中 `command -v ls`（返回 alias） | OHOS mksh 预置大量 applet 别名，alias 查找先于 PATH | 补丁 0003：plan 沙箱启动 `unalias -a`（恢复沙箱隔离语义；bash 非交互本无别名；plan 自定义别名不受影响） |
| 5 | `roundup --version` 报 0.0.5 | 上游 tag 内漏更版本号 | 补丁 0003：ROUNDUP_VERSION 对齐 0.0.6 |

## 源码修改

- patches/0001-edge-test.sh.patch —— 上游测试可移植性修改（空 PATH → /nonexistent，2 处）
- patches/0003-roundup.sh.patch —— set -E 探测降级 / PATH 备份恢复 / unalias -a / 版本对齐
- patches/0002-ohos-test.sh.patch —— 新增鸿蒙消费者可行性 plan（4 用例：PATH 安装、ROUNDUP_VERSION 探测、mktemp、/bin/sh）

## 依赖版本

无外部依赖（纯 POSIX shell；运行时要求 /bin/sh、coreutils/toybox applets）。

## 验证结果

```bash
# conan create / conan-verify 见 .ci-result.json 与 reports/
# 上游测试（OHOS mksh 实测）:
$ ./roundup
Tests:   18 | Passed:  15 | Failed:   3   # 3 个失败均为上游设计性失败
```

## 注意事项

- 本包为 **application（CLI 工具）**，commands.json 已在软件级别目录声明（R38）
- test_package 以自举方式运行被测 roundup（R34 实质依赖）执行 ohos-test.sh 消费者用例
- 语言预检（R47）判定 detected=c（构建系统=Makefile 归入 c 族，c↔cpp 兼容族）；实质为纯 shell 项目，已按 CI 能力矩阵 bash 脚本类（✅）路径适配
---

**编译结束**: 2026-09-27 02:09
**最终状态**: published
