# E549 — OHOS uname -r 含空格，Makefile 内插 $(shell uname -r) 生成损坏编译宏

> Contributor: Awstme | Status: Draft | Updated: 2026-09-05
> Source: bmagic 7.13.4 适配（BitMagic 平台 mk 的 OS_VER 宏在 OHOS 上损坏）

## 错误特征

```text
$ uname -s
HarmonyOS
$ uname -r
HongMeng Kernel 1.12.0

# make -n 干跑展开出的编译命令（BitMagic platforms/aarch64-linux-gnu.mk）：
clang++ -c -D_REENTRANT -D__HarmonyOS_HongMeng Kernel 1_12_0 -std=c++17 ...
clang: error: no such file or directory: 'HongMeng'
clang: error: no such file or directory: 'Kernel'
clang: error: no such file or directory: '1_12_0'
```

## 触发条件

- 构建系统: Makefile（平台 mk / 直接内插 `$(shell uname ...)` 的场景）
- 阶段: compilation（参数展开即损坏，可能表现为莫名 "no such file or directory"）

## 根因分析

OHOS 的 `uname -r` 返回含空格的 `HongMeng Kernel 1.12.0`（`uname -s` 为
`HarmonyOS`）。任何把 uname 输出内插进单个编译参数的 Makefile 都会把空格
带进去，单个 `-D` 宏被 shell/编译器拆成多个 argv：`-D__HarmonyOS_HongMeng
Kernel 1_12_0` 中 `Kernel`、`1_12_0` 被当作输入文件名。上游在标准 Linux
（uname -r 如 `5.15.0-91-generic` 无空格）完全正常。

BitMagic 实例：`OS_VER = -D__$(shell uname -s)_$(shell uname -r | sed -e 's/\./_/g' -e 's/-.*//')`。

## 解决方案

### 推荐方案
用上游预留的 make 变量顶层覆盖平台标签宏（BitMagic 为 `OS_VER`），单 token
等价定义，零补丁：

```sh
make -C tests/stress OSNAME=aarch64-linux-gnu OS_VER="-D__HarmonyOS_HongMeng__" ...
# 先 make -n 干跑确认展开后的命令不含空格宏
```

上游无预留变量时，顶层覆盖整段 `PLATFORM_CXXFLAGS`/`CFLAGS`（平台 mk 均为
`?=`/`=` 赋值，命令行变量优先）。

### 禁止做法
- ❌ 修改上游 mk 给 uname 输出加引号/转义（能用变量钩子就不改上游文件）
- ❌ 用 `sed -i` 事后替换生成物（不伪装修复生成物）

## 验证
```bash
uname -r   # 输出含空格即存在风险
make -n <target> | grep -c 'HongMeng Kernel'   # 修复后应为 0
```

## 关联条目
- 相关: E160（config.guess 不识别 HarmonyOS——同一"平台探测在 OHOS 失效"家族，
  但本条是 uname 输出内插损坏，机制不同）、E011（HMDFS umask 077）、E547（lld 入口损坏）、E036（平台字符串含空格导致构建路径错误，同族先例）
