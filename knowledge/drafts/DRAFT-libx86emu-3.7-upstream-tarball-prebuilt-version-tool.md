# DRAFT — libx86emu 3.7：上游发布 tarball 缺版本文件且携带异架构预编译工具

> 配对文件：`DRAFT-libx86emu-3.7-upstream-tarball-prebuilt-version-tool.kv`
> 库：libx86emu 3.7（wfeldt/libx86emu）｜任务：libx86emu-3.7-r01-bootstrap-and-adapt-pc3-31-20260927T110421Z

## 问题

上游 3.7 tag tarball **不含 VERSION 文件**，且携带维护者平台（x86_64 Linux）预编译的
`git2log` 二进制。在 aarch64/OHOS 上：

```text
/bin/sh: ./git2log: No such file or directory
/bin/sh: cat: VERSION: No such file or directory
cut: VERSION: No such file or directory
make: *** [Makefile:35: changelog] Error 127
make: install: No such file or directory
```

`./git2log` **文件存在**（23638 字节、可执行位齐全），报错却与"文件不存在"完全相同——
根因是异架构 ELF 缺少解释器 `/lib64/ld-linux-x86-64.so.2`。该错误极具误导性。

## 根因

1. 上游用自研 `git2log` 从 git 历史生成 `VERSION` / `changelog`；GitHub tag tarball
   不含 `.git` 与生成物，因此缺 `VERSION`。
2. Makefile 顶层 `VERSION := $(shell $(GIT2LOG) --version VERSION ; cat VERSION)` 依赖
   `git2log`；它不可执行时 VERSION 为空，`LIB_NAME = libx86emu.so.$(VERSION)` 命名错乱，
   `changelog` 目标必失败。
3. 随包分发的 `git2log` 是 x86_64 预编译 ELF，aarch64 上缺解释器 → 误导性
   "No such file or directory"。
4. 本机/CI 缺 coreutils `install` 命令 → `make install` 直接失败。

## 方案

1. 构建前显式写版本文件：`echo 3.7 > VERSION`。
2. 构建时移除/规避预编译工具：`mv git2log git2log.upstream`，使 Makefile 的
   `[ -x ./git2log ]` 探测回退 `true`，`VERSION` 由 `cat VERSION` 确定，行为跨环境确定、
   日志干净。
3. 纯 Makefile 无 configure：配方不套 autotools 模板，build() 直接
   `make shared CC=clang -j1`（跳过 changelog 依赖链）。
4. package() 不依赖 `install` 命令：conan `copy` + `ln -s` 手工落位 .so 与头文件。
5. 测试 harness 硬编码 `mktemp /tmp/...`（/tmp 只读，E002 场景）：等价替换为
   `$ENV{TMPDIR} || "/tmp"`（CI /tmp 可写时默认 /tmp；本地 TMPDIR 生效）。

## 验证

- 本地：`make shared CC=clang -j1` → `libx86emu.so.3.7`（424384 字节，32 个导出符号）。
- 上游测试：60 例 .tst，42/42 有 .done 期望输出的用例全部 ok，0 失败，18 例上游未提供
  .done 属 unchecked（nasm/2.16.03 由 ohpcd 制品仓提供）。
- Conan：`conan create archives/l/libx86emu/3.7 -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` G2 通过；conan-verify
  G0-G4/L2/L4/L5 全 PASS；test_package 功能测试（mov ax,0x1234; hlt → R_AX=0x1234）1/1 通过。
- W3 本地 CI：build_and_test.sh L0-L5 全 pass，100% (1/1)。

## 适用边界

- 发布 tarball 缺构建期 git 派生版本文件（VERSION/version.h 等）；
- 随包分发异架构预编译辅助工具（git2log/makedepend 类）；
- 纯 Makefile、无 configure 的 C 库的 OHOS conan 配方；
- 测试 harness 硬编码 /tmp 且环境 /tmp 只读（E002 实例）。

## 反例与限制

- tarball 自带 VERSION、或工具可由源码重编译、或版本号不依赖 git 派生时，本方案不适用；
- 不得把"预编译工具异架构"误判为源码缺陷或上游 bug；
- 移除预编译工具仅限构建期、可逆（改名而非删除），不落入 patches/ 平台宏禁区（无
  __OHOS__ 注入，属构建环境适配）；
- 该条目为路径 B 草稿，未经人工 promote 前不写入正式 E###、不更新 index.tsv。

## 审计

- 本文件 SHA-256：见 `knowledge/drafts/DRAFT-libx86emu-3.7-upstream-tarball-prebuilt-version-tool.md`（与 .kv 成对）。
- 字段一致性：.kv 的 error_signature/root_cause/rec_approach/affected_scope/
  verification_cmd 与本 .md 各节一一对应。
