# otpw 1.5 — HarmonyOS PC 适配笔记

- 上游: https://www.cl.cam.ac.uk/~mgk25/otpw.html （OTPW one-time password login package）
- 取源: `https://www.cl.cam.ac.uk/~mgk25/download/otpw-1.5.tar.gz`
  sha256 `98aca38a61c7713677b96f24426ca7053480c0fd077d91b1e99bc9f92ccb832a`
  （与 SCT 台账 Debian 索引 Checksums-Sha256 逐字节一致；PF7 拉黑 Debian 池 URL，仅作交叉校验）
- 构建系统: 裸 Makefile（M18 烧路径族）
- 状态: built（本地 conan create 真实通过，未 upload）
- 交付面: CLI `otpw-gen`（PAM 模块与 demologin 因平台无 PAM 生态不交付，见下）

## 症状

1. `make` 默认目标构建 `pam_otpw.so`，需 PAM 头与 `-lcrypt -lpam -lpam_misc`——鸿蒙
   musl 无 PAM 生态，直接构建即失败。
2. `install:` 目标烧死 Debian 路径（`PAMLIB=/lib/x86_64-linux-gnu/security`）、用 `rsync`
   安装、还会改写 `/etc/pam.d/sshd`——在鸿蒙上不可用也不可取。
3. `otpw-gen` 无参数运行报 `Can't access your passwd database entry!` 退出 1——鸿蒙 SSH
   会话的 uid（20001006）在 `/etc/passwd` 无条目（文件里只有 root/系统用户）。

## 根因

1. 上游 Makefile `TARGETS=otpw-gen demologin pam_otpw.so pam_otpw.8.gz otpw-gen.1.gz`，
   PAM 面是 Linux-PAM 专用；musl 没有 PAM 头与库。
2. `install-pam` 依赖 Debian 特化路径与 rsync/perl 改 PAM 配置，属发行版集成逻辑，
   不属于跨平台配方的职责（M18 烧路径族同型）。
3. `otpw-gen` 生成密码列表时要把哈希文件写到 `$HOME/.otpw`（由 `otpw_getpwuid(getuid())`
   查出 home），无 passwd 条目即 fatal。

## 最小复现

```sh
make TARGETS=pam_otpw.so            # → fatal error: security/pam_modules.h: No such file
./otpw-gen                          # → Can't access your passwd database entry! (rc=1)
```

## 已试过的失败方案（防重复踩）

1. **`otpw-gen -m` 免交互**：不行——实测 `-m` 仍先要 stdin 输入两次 prefix password。
   免交互的正确姿势是 `printf 'pw\npw\n' | otpw-gen ...` 直接喂 stdin。
2. **`-e 8` 降低熵要求绕过熵收集失败**：不行——熵下限 30 bits（`Entropy must be at
   least 30 bits!`）；实测 `-e 30` 可走通（/dev/urandom 在外部熵命令列表内）。
3. **在无 `-f` 下测试正向生成**：不行——先撞 passwd 查询 fatal。**必须带 `-f <file>`**
   （fnout 显式指定后跳过 `otpw_getpwuid`）。
4. **依赖 `ps lax`/`last | head -50` 外部熵命令**：鸿蒙 toybox 的 ps 不支持 lax、无 last、
   `/proc/net/tcp` 无权限读——这些熵源输出为空只是 warning，真正决定成败的是
   /dev/urandom 与 `-e` 下限。
5. **usage/help 路径直接裸跑**：不行——`help` 分支在 passwd 查询**之后**（otpw-gen.c:773
   在 745 之后），无 `-f` 时先报 passwd fatal。测 usage 必须带 `-f`。

## 最终方案

1. **构建**：`make -j1 TARGETS=otpw-gen`，CC 由 conan conf（tools.build:compiler_executables.c）注入 ——Makefile 变量命令行覆盖，
   零补丁裁掉 PAM/demologin 面；`CC=gcc` 裸赋值只有命令行赋值能覆盖（M18）；
   `CFLAGS=-O -ggdb -W -Wall -Wno-unused-result -fPIC` 是整体赋值，不覆盖保留上游默认。
2. **打包**：package() 自拷 `otpw-gen` 到 bin/（不跑 make install），README/otpw.html 入
   licenses/；`package_type=application`、bindirs=["bin"]；commands.json 声明（R38）。
3. **license 定案**：otpw.html 明示 GPL v2 or later（README 无 license 段，勿写 MIT/BSD）。
4. **测试面**：上游 0 测试（清点证据 `reports/upstream-test-scan.txt`；唯一 `test-login`
   目标是 ssh 回环手工验证指引，非自动化测试）。test_package 新增 19 条消费者断言：
   正向生成（`-f`+stdin 喂密码+`-e 30`，断言页头/编号行/行数/哈希文件/随机性/`-p 1`/`-o`、两次密码不一致拒绝生成）、
   `-r` 建议路径、usage 与坏参数路径（带 `-f`）、产物面（ELF/TARGETS 裁剪生效）。

## 适用边界

1. **本包不交付 PAM 功能**：`pam_otpw.so`/`demologin` 不构建、不打包；`test-login` 手工
   验证路径在无 PAM 的鸿蒙上无意义。若上游/评审需要 PAM 面，需先立项 PAM 生态包
   （本 PR 不捎带，R36/PF4）。
2. **`otpw-gen` 正向生成的 passwd 依赖**：不带 `-f` 的默认形态（哈希写到 `$HOME/.otpw`）
   在 uid 无 passwd 条目的主机上不可用——这是上游按 Unix 登录环境的设计，不是缺陷；
   本包测试全部走 `-f` 显式路径。
3. 鸿蒙 /tmp 只读（E002）：测试产物一律写按进程号分址的 scratch 目录；toybox sh 的
   `$(…)` 会往 /tmp 落临时件 ⇒ test.sh 零命令替换零反引号，计数用 `$(( ))`。
4. 无补丁：TARGETS 命令行覆盖 + package() 自拷贝已覆盖全部适配面，补丁数为 0
   （PF5 平台宏闸自然通过）。

## 测试数字口径

- 上游测试: 0（`upstream_tests_exist: false`，证据 `reports/upstream-test-scan.txt`）
- 新增消费者断言: 19 条（test_package/test.sh，真执行打包二进制）
- 彩排实测（2026-09-26，主理-61，clang 本机编译）: discovered=19 pass=19 fail=0 skip=0、
  `VERDICT: PASS`、`HMBS_TEST_PACKAGE_RESULT={"discovered":19,"passedCount":19,"skipped":0}`
- 正式门禁读数以本次 conan-verify / CI 判决为准，PR 正文数字与之一致。
---

**编译结束**: 2026-09-26 03:46
**最终状态**: built
