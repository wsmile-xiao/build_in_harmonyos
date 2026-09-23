# vc-dwim 1.10 — 鸿蒙PC (aarch64-linux-ohos) 适配说明

GNU vc-dwim 1.10：版本控制系统无关的 ChangeLog 工具对——
`vc-dwim`（Perl 脚本，检查 ChangeLog 条目与工作区 diff 一致性、展示/提交 diff）
与 `vc-chlog`（POSIX sh 脚本，从 unified diff 生成 GCS 风格 ChangeLog 条目）。

- 上游：https://ftp.gnu.org/gnu/vc-dwim/ （tarball 官方源，R39）
- 语言构成：纯脚本包（Perl + sh），无 C 编译产物（lang-preflight 判 mixed，
  本任务按用户指令完成适配，result 按实际状态上报并在此记录偏差）
- 构建方式：绕过 autotools，由 conanfile.build() 完成 automake 等价的
  `@VAR@` 模板替换（abcselect/1.5 先例）

## OHOS 适配点（patches/0001）

1. **perl 模块目录可重定位**：原版将 `@datadir@/@PACKAGE@` 烤成绝对前缀；
   补丁改为 datadir 不存在时按脚本自身位置回退 `../share/vc-dwim`，
   保证 Conan 包任意部署位置可用。
2. **umask 077 → 022**（E129）：HMDFS setgid + umask 077 使脚本临时目录
   （mktemp -d "$TMPDIR/vccXXXXXX"）连属主都不可写，vc-chlog 多文件处理
   全部失败；改为 022。上游 configure/config.status 亦需同样处理（构建期）。

## 运行时依赖

- perl 5.42（系统 `/data/service/hnp/bin/perl`，`#!/usr/bin/env perl` 解析）
- **Pod::PlainText**：perl 5.42 已从核心移除 → conan 依赖 `perl-pod-parser/1.67`
  （其 runenv_info 注入 PERL5LIB）
- **ctags**（可选功能，vc-chlog 函数名提取）→ conan 依赖 `ctags/6.2.1`
- GNU patch 2.7.6 / GNU awk 5.4.0（系统：`/usr/bin/patch` 为 toybox，
  功能受限；已从 cmd-pkgs 安装 GNU patch 至 `~/usr/local/bin`）
- git（vc-dwim 对 git 仓库操作）

## 上游测试（R51 三步法）

- 清点：`tests/` 共 25 个测试脚本（automake parallel harness）
- 实测（本机真机）：`make check -C tests` → **19 PASS / 6 SKIP / 0 FAIL**
- SKIP 明细（环境缺可选工具，非包缺陷）：
  - initialize / two-vc / subdir-cvs：需要 hg / cvs
  - author-bzr / symlinked-changelog：需要 bzr
  - git-worktree：需要 git man viewer（`git help` 输出通道）
- 通过前提：PERL5LIB 指 perl-pod-parser 包、PATH 含 GNU patch/ctags、
  TMPDIR 可写、umask 022

## 本版配方要点（L3）

- conanfile.build() 内联替换 `@VERSION@/@PACKAGE@/@PACKAGE_BUGREPORT@/
  @PATH_SEPARATOR@/@SHELL@/@AWK@/@CTAGS@/@PATCH@/@ctags_strip_type_column@`
  （Universal Ctags `-x` 输出含类型列 → strip=yes）
- package_type=application + commands.json（R38，工具型包）
- test_package 经 VirtualRunEnv 以 self.run 驱动 test_vc_dwim.py：
  --version 冒烟 + `vc-dwim --diff`（真实 git 仓库）+ `vc-chlog --stdin`
  （真实 diff → ChangeLog 条目）
---

**编译结束**: 2026-09-21 15:47
**最终状态**: built
