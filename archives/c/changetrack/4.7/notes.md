# changetrack 4.7 适配笔记

## 编译环境

- 构建系统: makefile（仅 test/install 两 target，无 configure/编译）
- 编译日期: 2026-09-07（首版）；2026-09-07（接入 rcs/5.10.1 后更新）
- 编译器: 无（纯 Perl 5 脚本）
- 状态: built

## 编译步骤

1. 下载源码：上游 SourceForge 只发布到 4.5，4.7 的权威发布物为 Debian pool 的
   `changetrack_4.7.orig.tar.gz`（17,716 字节，SHA256 与 `changetrack_4.7-11.dsc` 一致）。
2. `conan create archives/c/changetrack/4.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
3. build() 仅应用补丁（shebang）；打包由 package() 手工完成（脚本 + man + 示例 conf + README），
   因为上游 `make install` 硬编码 `/usr/local`、`/etc`，不可直接使用。
4. 依赖 rcs/5.10.1（archives/r/rcs，姊妹 run）：`requirements()` 声明，RCS 套件二进制
   经包 bindirs 进入消费方 PATH。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 直接执行报 "bad interpreter: /usr/bin/perl: not found" | 鸿蒙无 /usr/bin/perl，perl 在设备工具链用户态目录 | patch 0001：shebang 改为 `#!/usr/bin/env perl`（同 convmv 先例） |
| 2 | 变更检测静默产出空 .ed 脚本（toybox 遮蔽 `diff -e`：open 管道成功、stderr 报错、stdout 为空；`die "Can't do diff -e:$!"` 仅在 diff 完全不可执行时触发） | 脚本核心路径依赖 `diff -e`（ed 脚本输出）；toybox 0.8.12 diff 不支持 `-e`（"Unknown option 'e'"），且设备默认 PATH 中 /usr/bin(toybox) 先于工具链用户态目录 | 运行期 PATH 保证 GNU diffutils（设备工具链用户态自带）先于 toybox；CI profile buildenv PATH 已满足。test_package 的 .ed 内容断言（2c/CHANGED）可检出被 toybox 遮蔽的情形 |
| 3 | 上游 `make test` 失败 "RCS is not installed." | test.sh 检查 which perl + perl 模块 + `rcs -V`；RCS 套件（co/ci/rcs）设备与制品仓原本均不可得 | rcs/5.10.1 移植完成后解锁（见下节）；test_package 以 `requires("rcs/5.10.1")` 依赖 rcs 包并在测试中前置其 bindir |
| 4 | ci/co 报错/锁定信息异常 | RCS 检查需要非空 LOGNAME（空 LOGNAME 在鸿蒙 musl 环境下取登录名失败） | 测试命令显式 `LOGNAME="${LOGNAME:-$(id -un)}"`；姊妹 run 对 rcs 本身也有 patch 0004（treat-empty-login-as-unset）兜底 |

## 源码修改

- `patches/0001-changetrack.patch`（portability）：`#!/usr/bin/perl` → `#!/usr/bin/env perl`，仅此一处。

## 依赖版本

- rcs/5.10.1（conan requires；上游 make check 60/63，t790/t900/t999 为 HMDFS 平台固有限制）
- perl 5.42.0（设备工具链用户态自带，核心模块 File::Copy/Getopt::Std/File::Path/FileHandle/strict 齐备）
- GNU diffutils 3.10（diff -e 实测输出正确 ed 命令；toybox 0.8.12 diff 无 -e）

## 上游测试门禁（结论：PASS，7/7）

上游唯一测试入口为 `make test` → `test.sh`，内容为环境检查（which perl、5 项 perl 模块
`use` 探测、`rcs -V`），无功能断言。

- 历史：RCS 套件缺失期间按 NOT_RUN 合理穷尽记录（设备 PATH 无 rcs/co/ci；ConanCenter 无
  rcs recipe（404）；ohpcd 制品仓无 rcs；test_package 内嵌 rcs 源码构建属额外依赖构建须用户
  决定）。用户选择"先移植 rcs 解锁上游测试"，姊妹 run（rcs-5.10.1，commit dc91ea4）交付后
  本 run 以其 delivery base rebase 并声明 `requires("rcs/5.10.1")`。
- 现状：人工在设备上完整执行上游 `make test` 通过（7/7，实录日志存 run 目录
  logs/upstream-make-test-pass.log）；test_package Test 6 在每次 conan create 中按 test.sh
  原始检查逐项等价复验（which perl + 5 模块 + rcs -V）。
- 功能覆盖：上游测试仅为环境检查，test_package 另以 22 项功能断言补强（smoke 4 项 +
  无 RCS 回环 9 项 + rcs ci/co 往返 4 项 + 全模式 RCS 回环 5 项），加上 3 项上游等价
  检查共 25 项断言。

## 验证结果

```bash
conan create archives/c/changetrack/4.7 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package: -v PASS / -h PASS / 无 RCS 回环 PASS / rcs ci-co 往返 PASS /
#               全模式 RCS 回环 PASS / 上游 make test 等价 PASS
#               （25 项细粒度断言 / 8 组命名断言，口径以 test_package/MANIFEST.yml 为准：
#                 smoke 4 + 无 RCS 回环 9 + rcs ci/co 往返 4 + 全模式 RCS 回环 5 + 上游 make test 等价 3）
# 上游 make test（设备真实执行）: PASS 7/7
# 权威 CI: ci/conan/build_and_test.sh（CI_PACKAGES=archives/c/changetrack/4.7）PASS
```

## 注意事项

- 消费方运行 changetrack 时，PATH 必须保证 GNU diffutils 先于 toybox（diff -e 是核心路径，
  toybox diff 会直接报 Unknown option 'e'）。
- RCS 检查依赖非空 LOGNAME；空 LOGNAME 环境下 ci/co 会异常（详见知识草稿
  DRAFT-empty-login-identity-empty-success）。
- `-h` 退出码为 1 是上游设计（usage 后 `exit 1`），消费方勿以退出码判断 -h 成败。
- 测试/脚本如需在 build 语境（conanbuild env）使用 rcs 二进制，注意 buildenv_info 只向直接
  消费者传递一跳，需显式前置 rcs 包 bindir；conanrun env 则已传递。
