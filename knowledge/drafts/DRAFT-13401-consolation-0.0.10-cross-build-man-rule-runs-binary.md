# 上游 man 页规则执行编译产物:交叉构建必失败(consolation 0.0.10 载体)

- **草稿 ID**: DRAFT-13401-consolation-0.0.10-cross-build-man-rule-runs-binary
- **来源**: consolation/0.0.10 适配(积分赛依赖任务,PR 同分支提交)
- **分类**: autotools / man / cross-build / makefile
- **状态**: 随 PR #13401 提交(待 CI/审核)

## 问题 / 错误签名

- 上游 `src/Makefile.am` 内联规则:`../consolation.8: ../README consolation ...` → `./consolation | sed ... > consolation.8.new`——**man 页由执行刚编译出的守护进程排版生成**。
- 生成的 `src/Makefile.in` 把 `$(MANS)` 挂进 `all-am: Makefile $(PROGRAMS) $(MANS) config.h`,`make` 阶段即触发;交叉构建时 `./consolation` 是目标架构(aarch64)二进制,宿主无法执行 → `make` 失败(OSError: Exec format error / 无法运行)。

## 根因

1. help2man 风格的"运行程序生成 man 页"规则在**原生构建**下成立,交叉构建下天然不成立,但上游没有交叉构建守卫(无 `ifneq ($(CROSS_COMPILE),)` 之类)。
2. 该包 configure **没有** `--disable-manpages` 开关,无法用配置规避;
3. automake 的 man 页默认进入 `all` 目标(而非仅 install),所以失败发生在 `make` 而非 `make install`,更早、更隐蔽。

## 最小修复方案

configure 前中性化模板:把 `src/Makefile.in` 的 `dist_man_MANS = ../consolation.8` 行清空(`dist_man_MANS =`)。configure 从模板生成 Makefile 时继承空值 → `all-am` 不再包含 man 页、`install-man` 变 no-op。与其它包 `-Ddocumentation=false` / `--disable-manpages` 同口径("文档不构建")。

配方内实现(glob + 行替换,不占补丁位):见 `archives/c/consolation/0.0.10/conanfile.py` 的 `_neutralize_man_rule()`。

## 实际验证结果

- 本地树与 orig 全量 diff 确认:除 `src/input.c`(musl 补丁)外零改动;
- 补丁对干净 orig 树 `git apply --check` 通过;静态检查 6/6;
- 实际交叉构建由 CI `conan create` 完成(随 PR 提交时待跑)。

## 适用范围

- 上游 man 页/文档由"运行编译产物"生成(help2man、`--help` 重定向等)且无交叉守卫、无禁用开关的 autotools 包;
- 判别方法:grep Makefile.am 的 man 规则里是否出现 `$(bin_PROGRAMS)`/程序名作为命令执行。

## 非适用边界

- 已有 `--disable-manpages`/`-Ddocumentation=false` 开关的包,直接用开关,不要改 Makefile;
- man 页是**静态源文件**(dist_man_MANS 指向已存在的 .x/.8 文件、无执行规则)的包不受影响;
- 能接受在构建机跑目标二进制(如带 qemu-user 的环境)的场景不必中性化。

## 查重差异

- 仓库 doc/E00x 错误码系列记录过 TMPDIR/权限等构建环境问题;本条针对"man 规则执行产物"这一特定交叉构建失败形态,以 consolation/0.0.10 为载体,给出"清空 dist_man_MANS"的最小处理与判别方法。

## 关联交付

- 本草稿与 `archives/c/consolation/0.0.10/**` 属同一交付范围(同 PR 关联,知识库扩展路径 B)。
