# jchroot 1.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-26
- 编译器: clang
- 状态: built

## 编译步骤

1. 取上游 tag `v1.1` 的官方 archive：
   `https://github.com/vincentbernat/jchroot/archive/refs/tags/v1.1.tar.gz`
   （sha256 `a4393db5cf0bed756d3bdcddee0c91bd097c069854c421427b9e91a870c6936b`，
   archive 与 codeload 两端点独立下载比对一致）。
2. `conan create` 走标准两阶段：`source()` 拉取源码（`strip_root=True`），
   `build()` 在源码目录原地执行 `make -j1 CC=clang`。
3. `package()` 直接 copy 产物：`jchroot` → `bin/`，`jchroot.8` →
   `share/man/man8/`，`LICENSE` → `licenses/`。

上游 Makefile 全部内容只有 14 行，且**没有任何 `install` 目标**，因此不能走
`make install` 路线，只能直接安装产物。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 install 目标 | 上游 Makefile 只有 `all`/`jchroot`/`clean` 三个目标 | 配方在 `package()` 中直接 `copy()` 二进制与 man page |
| 2 | `refs/tags/1.1` 返回 404 | 上游 tag 实际为 `v1.1`（带 v 前缀） | conandata.yml 使用 `refs/tags/v1.1` |
| 3 | `CFLAGS` 为硬赋值而非 `?=` | `CFLAGS=-Werror -Wall -ansi -g -O2` 不可被 make 变量覆盖 | 实测 clang 15 在该组合下零告警，无需补丁、无需覆盖 |

以上 3 点均不需要修改上游源码，`patches/` 为空。

## 依赖版本

无 Conan 包依赖（上游无第三方库，Alpine 侧运行时依赖仅 `libc.musl-aarch64.so.1`）。
构建期仅用 OHOS 系统 C/POSIX 头：`sched.h`、`sys/mount.h`、`sys/prctl.h`、
`sys/syscall.h`、`mntent.h`、`pwd.h`、`grp.h`，以及 `clone()`/`unshare()`/
`__NR_pivot_root` 等 Linux 命名空间接口，OHOS PC 内核均提供。

## 验证结果

```bash
$ conan create . -pr:h=ohos-aarch64 ...
# build: make -j1 CC=clang → 零告警通过
# package: bin/jchroot + share/man/man8/jchroot.8 + licenses/LICENSE

$ conan-verify jchroot 1.1
exit 0

$ CI_PACKAGES="archives/j/jchroot/1.1" JUNK_PR_DIFF=... zsh ci/conan/build_and_test.sh
exit 0
```

CLI 冒烟（test_package 实测）：
`./jchroot --help` → 退出码 0，输出含 `Usage: ... [OPTIONS] TARGET [--] COMMAND`
与 `--new-user-ns` 选项表。

## 注意事项

- 该工具是需要 root 权限的运行时工具，冒烟测试只做 `--help` 解析验证（与上游
  CI `./jchroot --help` 一致），不实际进入 chroot。
- 产物**不可 strip**：与 abduco/mmc-utils 一样，OHOS 内核 MAC 对 strip 后二进制
  有额外限制，配方不调用 strip。
---

**编译结束**: 2026-09-26 18:28
**最终状态**: built
