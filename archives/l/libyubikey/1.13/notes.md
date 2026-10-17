# libyubikey 1.13 适配笔记

## 依赖结论（W0）

- 无运行时依赖、无构建依赖（上游 configure.ac 仅 `AM_MISSING_PROG([A2X], a2x)`，a2x 只在 maintainer 模式重新生成 man 页时需要；tarball 自带预生成的 modhex.1/ykparse.1/ykgenerate.1）。
- 无 Conan requires 声明，不需要拆分依赖适配。

## Conan 适配（本轮，2026-09）

- 配方：`conanfile.py`（AutotoolsToolchain + Autotools），`conandata.yml` 固定官方 tarball URL 与 SHA256。
- 构建：`build()` 执行 configure + `make -j1` + `make check`（上游回归套件）。
- 打包：`autotools.install()` + `licenses/COPYING`，手工删除 libtool `*.la`。
- package_info：`libs=["yubikey"]`，`bindirs=["bin"]`，runenv PATH 指向 bin/（modhex/ykparse/ykgenerate）。
- configure 参数：`A2X=true`（man 页已预生成，防止缺失 a2x 时干扰）。
- 默认 `shared=False`（静态库），与 2026-06 真机构建产物一致。
- test_package：CMake 消费测试 21 个断言 + 已安装 `modhex` CLI 冒烟 1 个断言，共 22 个（与 MANIFEST.yml/manifest.yaml 一致）。

## 源码与构建系统分析（W1）

- 上游：Yubico yubico-c（libyubikey），BSD-2-Clause，纯 C，无第三方依赖。
- 源码归档：官方 Release tarball（含完整 tests/selftest.c），SHA256 `04edd0eb09cb665a05d808c58e1985f25bb7c5254d2849f36a0658ffc51c3401`（本机已复核）。
- 构建系统：autotools + libtool；产物 libyubikey（static/shared 由 configure 决定）+ 3 个命令行工具 modhex/ykparse/ykgenerate + man 页。
- 上游测试：`make check` → tests/selftest（1 个测试二进制，17 个 assert：modhex-1.1/1.2/2/3、hex-1/2/3/4/5、aes-1.1/1.2、otp-1、crc-1/2/3/4）。

## 补丁

| 文件 | 原因 | 说明 |
|------|------|------|
| 0001-build-aux-config.guess.patch | E007 平台识别 | 2013-06-10 版不识别 HarmonyOS；替换为 automake-1.17 版（2023-08-22，含 `__OHOS__` 检测 → aarch64-unknown-linux-ohos） |
| 0002-build-aux-config.sub.patch | E007 平台识别 | 2013 版不识别 linux-ohos；替换为 automake-1.17 版（2023-09-13，canonicalize linux-ohos 三元组） |

两补丁均为脚本整文件替换，无 C 代码改动，平台检测类补丁。

## 真机 shadow CI 迭代记录

### r1（2026-09-27，job libyubikey-1.13-20260927）

- 排队 wait_seconds=0（锁空闲），L0 静态门禁全过，conan create 到 configure 阶段失败。
- 报错原文：`/system/bin/sh: .../configure: Permission denied` → `ConanException: Error 126`。
- 设备探针定位（两个独立根因，均为当日设备 HMDFS 行为）：
  1. **脚本 execve 被拒**：新建脚本 chmod 777 实际落盘 `rwxr-x---` 且 owner 显示 20001006（非当前会话 uid），任何直接 execve 返回 126；`sh script` / `bash script` 解释执行正常；**编译出的 ELF 二进制可直接执行**（工具链自动签名）。→ 修法：configure 经 `sh ./configure` 调用（anubis/4.3 配方同款），`CONFIG_SHELL=/bin/sh SHELL=/bin/sh`。
  2. **config.status mktemp 坑**（同 6 月问题 #4、abnfgen/anubis 配方先例）：`(umask 077 && mktemp -d "./confXXXXXX")` 产生的 setgid 目录不可写 → `could not setup config files machinery`。修法：configure 运行前把该分支替换为 `tmp=./conf$$-$RANDOM && mkdir "$tmp"`（configure 会把该段原样嵌入 config.status，必须改 configure 本身）。
- 探针全链路验证：`sh ./configure` → `make -j1` → `make check`（TOTAL=1 PASS=1）→ `make install DESTDIR` 全部通过，产物 bin/lib/include 齐全。
- 配方修复：build() 改为解释器调用 + mktemp 补丁 + TMPDIR 默认 ~/tmp（/tmp 只读）。

### r2（同 job）

- 报错原文：`checking for ar... no` → `checking the archiver (link -lib) interface... unknown` → `configure: error: could not determine link -lib interface`。
- 根因：CI conanbuild 环境 PATH 不含 `/data/service/hnp/bin`（CC 以绝对路径引用，clang 可用），ar/ranlib 解析不到。
- 解法：OHOS 时把 `/data/service/hnp/bin` 前置到 PATH（commit 1b402b5961）。

### r3（同 job）

- 编译、上游 `make check`（PASS: selftest, TOTAL=1 PASS=1）、安装全过；test_package 21 检查仅 `otp generate/parse roundtrip` 失败。
- 根因：test.c 断言 bug——`yubikey_generate()` 会**原地加密** token 结构体（yktoken.c），原断言拿加密后的 tok 与解密结果比对，必然不等。本机仅交叉编译未运行，未提前抓住（教训：能用解释器模拟跑的断言尽量本机先跑一遍）。
- 解法：保存原始字节常量，parsed 与常量比对（与上游 selftest otp-1 语义一致，commit 2e25a81ca7）。

### r4（2026-09-27 15:07，run codex-1.13-libyubikey-1.13-20260927-conan-20260927-150715-23005）——最终结果

```text
wait_seconds=0
exit code: 0
L0_RESULT=pass: all checks passed（含 L0j：registry 无 1.13，首次发布）
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: modhex --version OK（ykparse/ykgenerate --version 非零，仅记录）
L4_RESULT=warn: 补丁中 "targets" 注释含 "gets" 子串的已知误报
L5_RESULT=pass: bin/ has content
上游测试: TOTAL=1 PASS=1 FAIL=0 SKIP=0
test_package: 21 checks, 0 failures + modhex CLI 冒烟通过
Build Summary: Success 1 / Failed 0
```

## Test evidence

- 2026-06-06 ohc-run 真机构建（历史，ohc-run 流程）：
  - `make check`：TOTAL=1 PASS=1 FAIL=0 SKIP=0。
  - `modhex abcdefghijklmnopqrstuvwxyz` → `hbhdhehfhghhhihjhkhlhnhrhthuhvicibidieifigihiiijikil`（真机实测）。
- 2026-09-27 Conan shadow CI r4：L0/L1/L2/L5 pass、L4 warn（误报）、exit 0；上游 1/1；test_package 21 断言 + CLI 冒烟全过。



## 历史：2026-06 ohc-run 真机构建经验（对 shadow CI 排障仍有用）

| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | C compiler cannot create executables | SDK lld 依赖 libxml2.so.16 找不到；用 GNU ld（`-fuse-ld=...`）替代 |
| 2 | cannot run C compiled programs (Permission denied) | OHOS 要求 ELF 签名；LD wrapper 链接后自动 sign-elf |
| 3 | config.guess unable to guess system type | 替换 config.guess/config.sub 为 2023 版（本轮已固化为补丁） |
| 4 | config.status subs1.awk Permission denied | HMDFS mktemp umask 077 组权限问题；mktemp wrapper umask 002 |

## 下一步（真机 shadow CI）

1. 在真机用隔离 job 执行单包 CI：
   ```sh
   sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
     --user codex \
     --job libyubikey-1.13-<timestamp> \
     --package archives/l/libyubikey/1.13 \
     --repo-source <existing-repo>
   sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
   ```
2. 记录 L0/L1/L2/L4/L5 结果、上游测试数量（预期 TOTAL=1 PASS=1）、test_package（预期 22/22）。
3. 关注点：若制品仓已存在 libyubikey/1.13 且配方不同（R37），需递增为 1.13.1 并同步目录/配方/test_package/MANIFEST/分支名。
