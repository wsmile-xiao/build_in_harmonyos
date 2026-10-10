# members 20080128.1-nmu3 适配笔记

## 编译环境

- 构建系统: makefile（裸 GNU Makefile；无 configure、无 CMake）
- 编译日期: 2026-10-01
- 编译器: NDK clang++（`/data/service/hnp/bin/clang++` → `aarch64-unknown-linux-ohos-clang++`），libc++ / musl
- 构建主机: x86_64 runner（交叉目标 aarch64-linux-ohos，`qemu-aarch64` 可用）
- profile: `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 语言预检（R47）

`detect_language` 判定 `cpp`（顶层 Makefile；源文件 1 个 `members.cc`，cpp 占比 100%），与任务语言一致，预检放行。

## 编译步骤

无补丁，无 configure。配方内实际驱动的编译：

```bash
make -C <src> CXX=/data/service/hnp/bin/clang++ -j1
```

上游 `Makefile` 用 `CXX ?= g++`、`CPPFLAGS ?= -g -Wno-deprecated`，命令行覆盖 `CXX` 即可；
`members: members.o` 由隐式规则 `members.o: members.cc` 编出。`members.cc` 触发 6 条 clang 告警
（字符串字面量转 `char *`、dangling else），均为上游代码告警，不影响产物，未改动。

## 上游测试清点（R51，附证据）

上游 `members_20080128.1+nmu3.tar.xz` 只含：`Makefile` `members.cc` `members.1` 与 `debian/`
（`changelog control copyright dirs manpages README.Debian rules salsa-ci.yml source/format`）。
无 `tests/` 目录、Makefile 只有 `members` / `clean` / `install` 三个目标（无 check/test）、
无 `debian/tests`（autopkgtest）、无 ctest 登记 ⇒ **上游测试 N = 0，N′ = 0**。
执行级验证全部由 `test_package` 的消费者程序承担。

## 源 URL

members 是 Debian 原生包（`debian/source/format` = `3.0 (native)`，作者 Jim Lynch 为 Debian 编写并在
Debian 内维护），不存在 Debian 之外的独立上游发布位，Debian archive pool 即唯一官方分发源。
`deb.debian.org` 属 PF7 的 Debian 域拦截范围，本包改取清华 TUNA 的 Debian archive 镜像
（权威高校镜像）：

| 源 | URL | HTTP | 大小 | sha256 |
|---|---|---|---|---|
| 官方池 | `https://deb.debian.org/debian/pool/main/m/members/members_20080128.1+nmu3.tar.xz` | 200 | 6928 | `a60f2bec44ec3909aeedef64db2a674c305c075f933a7ae1f3a2fb05cee4d381` |
| conandata 采用 | `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/m/members/members_20080128.1+nmu3.tar.xz` | 200 | 6928 | 同上（实测一致） |

（USTC 镜像对该路径返回 403 页面，未采用。）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make install` 不可用 | 上游 install 写死 `cp members $(DESTDIR)/usr/bin/members`，且要求目录预先存在 | 不调用 make install，`package()` 按 Conan 布局复制 `bin/members`、`share/man/man1/members.1`、`licenses/copyright` |
| 2 | `.work` 与 `.orig` 硬链接（E543） | init-build 解包产物为硬链接 | 解包后 `cp --remove-destination` 断链（本包无补丁，仅作防护） |
| 3 | 本机无法直接执行 OHOS 动态产物 | 缺 `/lib/ld-musl-aarch64.so.1`；qemu-user 无 binfmt，子进程 exec 不能透传 | 同源 `.o` 静态重链 + `members-qemu` wrapper（`exec qemu-aarch64 members-static "$@"`）做功能验证，见下 |

## 源码修改

无补丁。

## 依赖版本

无第三方依赖（libc / 标准库）。

## 验证结果

本地（x86_64 + qemu-aarch64，**静态重链副本**，不等于交付产物已实跑）：

```bash
clang++ -static -o members-static members.o          # 同源 .o 静态重链
clang++ -std=c++17 -static -o test_members-static test_members.cpp
printf '#!/bin/sh\nexec qemu-aarch64 members-static "$@"\n' > members-qemu; chmod +x members-qemu
qemu-aarch64 ./test_members-static ./members-qemu
# checks=35 failed=0  (rc=0)
```

消费者程序对 `root`、`sudo` 两个组逐项比对 `-s/-p/-t/-a/缺省/--secondary`，并验证
`--help`（rc 0）、无参数（rc 1 + Usage 走 stderr）、不存在的组（rc 1 + stderr）。
`conan create` 的 `test_package` 在 x86 构建机上只编译链接消费者、不执行（日志明确 warning），
在 aarch64（OHOS PC / CI worker）上必须运行并全部通过 —— **x86 上未原生执行交付产物，运行由 CI 执行**。

## 注意事项

- 上游 `display_primaries` 先多调一次 `getpwent`，主组成员枚举会跳过数据库第一条用户记录（上游既有行为，
  未改动；消费者用例按此约定断言：输出 ⊆ 全部主组用户、⊇ 除首条外的主组用户）。
- 组存在但没有任何成员时，`-a`/缺省模式因悬空 `else` 返回 1 且无错误信息（上游既有行为，未改动；
  消费者用例断言"退出码 == (输出为空 ? 1 : 0)"）。
- 运行结果取决于运行环境的组/用户数据库（`/etc/group`、`/etc/passwd` 或平台等价物）。
---

**编译结束**: 2026-10-01 20:03
**最终状态**: built
