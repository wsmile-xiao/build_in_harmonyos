# libyubikey 1.13 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-06
- 编译器: clang 15.0.4 / clang++
- 目标平台: aarch64-unknown-linux-ohos
- 内核: HongMeng Kernel 1.12.0
- 状态: published

## 编译步骤

1. **init-build**: 下载并解压 libyubikey-1.13.tar.gz
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build libyubikey 1.13 --url=https://developers.yubico.com/yubico-c/Releases/libyubikey-1.13.tar.gz
   ```

2. **源码补丁**: 更新 config.guess/config.sub (E007)
   - 原文件版本 2013-06-10，不识别 HarmonyOS / aarch64-unknown-linux-ohos
   - 替换为 automake-1.17 版本（2023-08-22 / 2023-09-13），正确识别平台
   ```bash
   cp /storage/Users/currentUser/usr/local/share/automake-1.17/config.guess build-aux/config.guess
   cp /storage/Users/currentUser/usr/local/share/automake-1.17/config.sub build-aux/config.sub
   ```

3. **环境适配工具**: 创建 LD wrapper 和 mktemp wrapper
   - LD wrapper: 链接后自动调用 sign-elf 签名 ELF 二进制（解决 Permission denied）
   - mktemp wrapper: 使用 umask 002 创建临时目录（解决 HMDFS 组权限问题）

4. **configure**: 使用 bash + GNU ld + mktemp wrapper
   ```bash
   PATH=/storage/Users/currentUser/tmp/mktemp-bin:$PATH \
   CONFIG_SHELL=/data/service/hnp/bin/bash \
   /data/service/hnp/bin/bash ./configure --prefix=$DEFAULT_PREFIX \
     LDFLAGS="-L/storage/Users/currentUser/usr/local/lib -fuse-ld=/storage/Users/currentUser/tmp/ld-wrapper.sh"
   ```

5. **make**: 单线程编译成功
   ```bash
   make -j1
   ```

6. **make install DESTDIR**: staging 隔离安装
   ```bash
   make install DESTDIR=$TEST_PREFIX HELP2MAN=/bin/true
   ```
   产物位于 `$TEST_PREFIX/$DEFAULT_PREFIX/`

7. **make check**: 全部测试通过
   ```bash
   make check
   # 结果: TOTAL=1 PASS=1 FAIL=0 SKIP=0 ERROR=0
   ```

8. **ELF 签名验证**: 签名并验证 staging 二进制可执行
   ```bash
   ohc-run.py sign-elf $STAGING_PREFIX/bin/modhex
   ohc-run.py sign-elf $STAGING_PREFIX/bin/ykparse
   ohc-run.py sign-elf $STAGING_PREFIX/bin/ykgenerate
   ```

9. **verify-build**: 质量门禁 G1-G4 通过

10. **package**: 预编译包制作成功（ohc-run.py package 9步管线）

11. **本地部署验证**: make install（不带 DESTDIR）+ 签名 + 功能验证
    ```bash
    make install HELP2MAN=/bin/true
    ohc-run.py sign-elf ~/usr/local/bin/modhex
    ~/usr/local/bin/modhex abcdefghijklmnopqrstuvwxyz
    # 输出: hbhdhehfhghhhihjhkhlhnhrhthuhvicibidieifigihiiijikil
    ```

12. **finish**: 收尾完成，状态 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C compiler cannot create executables | OpenHarmony SDK 的 lld 链接器依赖 libxml2.so.16，但 musl 动态链接器找不到该库 | 使用 `-fuse-ld=/data/service/hnp/bin/ld`（GNU ld）替代 SDK 内的 lld，GNU ld 不依赖 libxml2 |
| 2 | cannot run C compiled programs (Permission denied) | OpenHarmony 安全机制要求 ELF 二进制必须签名才能执行，configure 的 conftest 测试二进制未签名导致无法执行 | 创建 LD wrapper 脚本，链接完成后自动调用 `ohc-run.py sign-elf` 签名所有可执行 ELF 文件 |
| 3 | config.guess unable to guess system type | 源码自带 config.guess 版本为 2013-06-10，不识别 HarmonyOS 和 aarch64-unknown-linux-ohos 三元组 | 替换为 automake-1.17 版本的 config.guess（2023-08-22）和 config.sub（2023-09-13），正确识别平台 (E007 模式) |
| 4 | config.status subs1.awk Permission denied | HMDFS 文件系统下 mktemp -d（umask 077）创建的临时目录被 UID 20001006 拥有，而当前进程 UID 为 20020082，组权限仅为 setgid（无读/写权限），导致无法在临时目录内创建文件 | 创建 mktemp wrapper 脚本，使用 umask 002 替代 umask 077 创建临时目录，确保目录具有组可写权限 (drwxrws--x) |

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁文件 |
|------|------|------|----------|
| build-aux/config.guess | E007: 2013版不识别 HarmonyOS / aarch64-unknown-linux-ohos | 替换为 automake-1.17 版本 (2023-08-22) | 0001-build-aux-config.guess.patch ✅ |
| build-aux/config.sub | E007: 2013版不识别 HarmonyOS / aarch64-unknown-linux-ohos | 替换为 automake-1.17 版本 (2023-09-13) | 0002-build-aux-config.sub.patch ✅ |

## 依赖版本

- 无依赖（required 和 optional 都为空）

## 验证结果

```bash
# make check 真实执行输出
PASS: selftest
============================================================================
Testsuite summary for libyubikey 1.13
============================================================================
# TOTAL: 1
# PASS:  1
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
============================================================================

# 二进制功能验证
$ ~/usr/local/bin/modhex abcdefghijklmnopqrstuvwxyz
hbhdhehfhghhhihjhkhlhnhrhthuhvicibidieifigihiiijikil

$ ~/usr/local/bin/modhex -d ccbhcvlugnicnrtubnterhevtvivitb
（解码输出二进制数据）

$ ~/usr/local/bin/ykparse
Usage: ykparse <aeskey> <token>

$ ~/usr/local/bin/ykgenerate
Usage: ykgenerate <aeskey> <yk_internalname> <yk_counter> <yk_low> <yk_high> <yk_use>
```

## 交付物

| 文件                                | 大小    | 说明                          |
|-------------------------------------|---------|-------------------------------|
| libyubikey-1.13-ohos-aarch64.tar.gz | 267KB   | 预编译包（strip + ELF签名）   |
| libyubikey-1.13-ohos-aarch64-debug.tar.gz | 75KB | 调试符号包                    |

预编译包包含：3个二进制（modhex/ykparse/ykgenerate）、1个静态库（libyubikey.a）、1个头文件（yubikey.h）、3个man手册页

## 注意事项

1. 需使用 LD wrapper 签名脚本解决 OpenHarmony ELF 签名要求（链接后自动签名）
2. 需使用 mktemp wrapper 解决 HMDFS 目录权限问题（umask 002 替代 077）
3. 需使用 GNU ld (/data/service/hnp/bin/ld) 替代 SDK 的 lld（lld 依赖 libxml2.so.16）
4. 仅编译静态库（libyubikey.a），无共享库（configure 判定 linker 不支持 shared libraries）
5. CONFIG_SHELL 必须设置为 bash，避免 toybox sh 兼容性问题
6. G0 干净构建验证因 Python subprocess 平台限制失败，已手动验证构建可复现

---

**编译结束**: 2026-06-06 10:05
**最终状态**: published