# cisco7crack 0.0-git20121221.f1c21dd 适配笔记（HarmonyOS PC · 无构建系统）

## 定位
- 产出 CLI 工具 bin/cisco7crack（Cisco IOS type-7 口令加解密，单文件 C，GPL-2.0-or-later）。

## 源
- 版本串 0.0-git20121221.f1c21dd 对应上游 first commit f1c21ddf624a5d40e123ffebcd9fafbb47f86df0
  （2012-12-21，GitHub API 核实）。
- https://github.com/madrisan/cisco7crack/archive/f1c21ddf624a5d40e123ffebcd9fafbb47f86df0.tar.gz
- sha256: ae5c2e10665781fbb1d5e51ce59b8656f6a99521b32b9fe8cdb9b9a367fdcdce

## W0/W0b
- preflight_check.sh：无依赖声明，通过。
- 本仓库无同软件历史归档（archives/c/ 下无 cisco7crack）。
- lang-preflight：task=cpp，detected=c（c↔cpp 兼容族），单文件 cisco7crack.c（311 行），通过。

## 构建要点
- 快照内无 Makefile/configure；源码头注释给出参考命令
  `gcc -Wall -W -ansi -pedantic -O2 cisco7crack.c -o cisco7crack`。
- 配方 build() 用 profile 编译器（R33）：`clang -O2 -fPIE -D_GNU_SOURCE -Wall -W
  cisco7crack.c -o cisco7crack -pie -Wl,-z,relro,-z,now`（探索构建零错误）。
- package() 安装后 ELF 自签（HarmonyOS XPM；签名调用带 env -u LD_LIBRARY_PATH，
  防 profile buildenv 前置的 SDK llvm/lib 遮蔽 binary-sign-tool 的 libc++）。

## 行为向量（真机实测，test_package 断言依据）
- `-d 104D000A0618` → `Plain string     : cisco`（上游源码头注释自带示例，已知答案）。
- `-c#9 -q gHa5ecret1` → `094B66084C0014000E1855`（固定偏移 9，输出确定）。
- `-d 094B66084C0014000E1855` → `gHa5ecret1`（round-trip）。
- `-d 104`（奇数 hex 位）→ `WARNING: input truncated! (odd number of letters)`，exit 4。

## 上游测试账本（R51）
- 上游无测试：快照仅 cisco7crack.c / cisco7crack.h / README.md / .gitignore，
  无测试源码、无测试脚本、无构建系统（自然也没有 test/check 目标）。
  N_static = 0，N_executed = 0（如实申报）。
- 消费者测试（test_package）4 用例 / 4 断言：驱动真实二进制的已知答案解密、
  确定性加密、round-trip 与非法输入退出码。

## 状态
built —— conan create 真机验证通过后回填（见 .ci-result.json / reports/）。
---

**编译结束**: 2026-09-09 00:10
**最终状态**: built
