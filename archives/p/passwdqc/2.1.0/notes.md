# passwdqc 2.1.0 — OHOS 适配笔记

## 构建概要

- 构建系统：GNU Makefile（纯 C，无 autotools/cmake/meson）
- 编译器：clang（HNP SDK aarch64-linux-ohos），通过 `tools.build:compiler_executables` dict 注入
- 构建命令：Conan recipe 执行 `make -j1 CC=<profile 编译器> LD=<profile 编译器> utils_wrapped`
- 产物：libpasswdqc.so.1、pwqgen、pwqcheck、pwqfilter

## 首个编译错误

1. `make[1]: gcc: No such file or directory` — Makefile 默认 `CC = gcc`，OHOS 无 gcc
2. `pam_passwdqc.c:28: fatal error: 'security/pam_appl.h' file not found` — OHOS 无 Linux-PAM

## 根因

- OHOS 无 gcc，需用 HNP SDK 的 clang
- OHOS 无 Linux-PAM 生态，`security/pam_appl.h` 不存在
- pam_passwdqc.so 在 OHOS 上无运行时意义（无 PAM 框架）

## 修复方案

- conanfile.py build() 中通过 Make 命令行覆盖 CC/LD（编译器取自 `tools.build:compiler_executables` dict → `.get("c")`，R33）
- 跳过 pam_passwdqc.so 构建：仅构建 `utils_wrapped`（不构建 `all_wrapped`，后者依赖 `pam_wrapped`）
- 单独通过 `sed` 生成 passwdqc.pc（`make pkgconfig` 目标挂在 all 下，依赖 pam）
- make 使用 `-j1`，避免 jobserver FIFO 限制

## 测试结果

- 上游测试套件：6 个脚本实时执行，共 81 个子测试，81 PASS / 0 FAIL / 0 SKIP
  - test-pwqcheck-basic.sh: 18 PASS
  - test-pwqcheck-length.sh: 18 PASS
  - test-pwqcheck-multi.sh: 5 PASS
  - test-pwqcheck-similarity.sh: 8 PASS
  - test-pwqfilter-mode.sh: 12 PASS
  - test-pwqgen.sh: 20 PASS
- conan test_package：消费者视角测试，共 14 项断言全部通过
  - API 级测试（11 项）：强密码接受、弱密码拒绝、随机生成、唯一性、相似性检测、空密码拒绝、长密码接受、宽松/严格配置、配置文件加载
  - CLI 工具测试（3 项）：pwqgen 生成密码、pwqcheck 接受强密码、pwqcheck 拒绝弱密码
  - 交叉编译（CI 场景）仅编译不运行，本地可运行
  - CLI 工具运行需设置 LD_LIBRARY_PATH 指向 libpasswdqc.so 所在目录

## conan create 结果

- 退出码：0
- 包引用：见 `.ci-result.json`

## 备注

- libpasswdqc 核心库零外部依赖（`LDLIBS_lib =` 为空）
- pam_passwdqc.so 需 `-lpam -lcrypt`，OHOS 均不可用，已跳过
- 警告：`DPACKAGE="passwdqc"` 在 clang 下触发 `-Winvalid-pp-token`，不影响构建
- man 复制需显式列出 man1 文件名，避免 `*.1` 通配符误匹配 `libpasswdqc.so.1`
---

**编译结束**: 2026-09-04 16:03
**最终状态**: built
