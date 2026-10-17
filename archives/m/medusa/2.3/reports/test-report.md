# medusa 2.3 验证报告

## 1. 环境

| 项目 | 值 |
| --- | --- |
| 归档路径 | `archives/m/medusa/2.3/` |
| 分支 | `feat/medusa-2.3`（worktree `D:\harmonyos\worktrees\medusa`） |
| 真机 | HarmonyOS (OHOS) aarch64，clang 15.0.4，Conan 2.29.1 |
| 真机 profile | `ohos-aarch64-localdevice`（编译器路径 `$HOME/usr/local/bin/clang`） |
| 隔离环境 | `$HOME/ohos-users/medusa/medusa-2.3-build`（独立 `CONAN_HOME` + `RUN_DIR`） |
| 入口 | `ohos-test-runner.sh --user medusa --lib medusa --mode heavy --try-lock` |
| 本机 | Windows + MSYS；用于补丁生成与静态校验 |

## 2. W0 依赖发布检查（R35/R36/R39）

```sh
bash ci/scripts/preflight_check.sh medusa/2.3 \
  --deps "openssl/3.0.21 libssh2/1.11.1 libgcrypt/1.11.0 libsmb2/6.2"
```

```text
[OK] 已发布: openssl/3.0.21
[OK] 已发布: libssh2/1.11.1
[OK] 已发布: libgcrypt/1.11.0
[OK] 已发布: libsmb2/6.2
[OK] 版本号未被占用: medusa/2.3
```

`libsmb2/6.1` 不存在（加速策略拒绝），6.2 为唯一可用版本。
`medusa/2.3` 不在制品仓中，符合 R37「首次适配用上游版本」。

## 3. 源码校验

| 项目 | 值 |
| --- | --- |
| URL | `https://github.com/jmk-foofus/medusa/releases/download/2.3/medusa-2.3.tar.gz` |
| 来源 | 上游 GitHub Release 官方资产 |
| 大小 | 409426 字节 |
| sha256 | `b0b7b75b562f96134cb95aa58e867d580b7c526c7a07e37f955ad3c3c3c8e251` |

真机无法直连 github.com，按 sha256 文件名把该 tarball 注入
`$HOME/conan_dl_cache/s/`，Conan 直接命中本地缓存（日志：
`Source [...] retrieved from local download cache`）。CI 侧的镜像 fallback 由
`build_and_test.sh` 自动追加，两者都指向同一官方资产与同一 sha256。

## 4. 补丁验证

7 个补丁在**原始解包树**上逐个验证可应用（`git apply --check -p1` 单枚独立检查），并按
0001→0007 顺序验证可连续应用；两种方式 7/7 全部通过（在原始 tarball 解包树上复现，
非采信配方自述）：

```text
individual 0001-config.guess.patch                              OK
individual 0002-config.sub.patch                                OK
individual 0003-configure-ohos-link-flags.patch                 OK
individual 0004-configure-config-status-tmpdir.patch            OK
individual 0005-thread-pool-no-cancel-capability.patch          OK
individual 0006-ohos-ssh-module-gcrypt-wrapper.patch            OK
individual 0007-pthread-cancel-capability-guard.patch           OK
sequential apply 0001..0007                                     OK
```

整套补丁共触及 6 个文件：`config.guess`、`config.sub`、`configure`、`configure.ac`、
`config.h.in`（生成物同步）与 `src/medusa-thread-pool.c`（产品源码）。

`config.guess` / `config.sub` 行为验证（stub `uname`）：

```text
config.guess (HarmonyOS)        → aarch64-unknown-linux-ohos
config.guess (Linux, 回归)       → aarch64-unknown-linux-gnu
config.sub aarch64-linux-ohos   → aarch64-unknown-linux-ohos
config.sub x86_64-pc-linux-gnu  → x86_64-pc-linux-gnu
```

真机 configure 实测：

```text
checking build  system type... aarch64-unknown-linux-ohos
checking host   system type... aarch64-unknown-linux-ohos
checking target system type... aarch64-unknown-linux-ohos
```

## 5. 真机 conan create 结果

RUN_DIR：`$HOME/ohos-test-runs/medusa-medusa-medusa-2.3-final-20260929-170943-34668`

```text
configure:     SSH             Enabled
medusa/2.3: bundled OpenSSL providers from .../p/opens3b77e8c5f6d9b/p/lib/ossl-modules
[info] modules dlopen'ed successfully: 22
[ok] core modules (http ftp smtp telnet vnc) loaded via dlopen
[ok] ssh module loaded (libssh2 + libgcrypt)
ALL MEDUSA TESTS PASSED
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: medusa version/help failed
L4_RESULT=warn: dangerous functions in patches
L5_RESULT=pass: bin/ has content

━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
```

`conan create` 全链路通过：source（本地缓存命中）→ patch（7 个全部应用）→
configure（三元组/OpenSSL/libssh2/libgcrypt 全部探测成功）→ make（核心 + 22 个模块）→
package（含 ELF 签名）→ test_package（22 个模块 dlopen 成功 + 完整消费者用例通过）。

## 6. 产物与运行验证

| 产物 | 说明 |
| --- | --- |
| `bin/medusa` | 883200 字节，含 `.codesign` 段（真机可执行） |
| `lib/medusa/modules/*.mod` | 22 个协议模块（含 `ssh.mod`、`smbnt.mod`） |
| `lib/ossl-modules/legacy.so` | 3238272 字节，随包分发的 OpenSSL legacy provider |
| `share/man/man1/medusa.1` | 上游 man page |

自包含运行（只用包内目录）：

```text
$ OPENSSL_MODULES=<pkg>/lib/ossl-modules MEDUSA_MODULE_PATH=<pkg>/lib/medusa/modules \
    <pkg>/bin/medusa -V        → 成功（rc=0）
$ ... <pkg>/bin/medusa -d      → 22 个模块
```

核心程序动态符号表导出 149 个 `EVP_*` 符号，模块通过它解析 OpenSSL 调用
（模块自身的 `NEEDED` 只有 `libc.so`、`libgcrypt.so.20`、`libgpg-error.so.0`、`libssh2.so.1`）。

## 7. 门禁说明

| 门禁 | 结果 | 说明 |
| --- | --- | --- |
| L0a–L0n | pass | 含 L0k `commands.json`、L0m 目录结构、L0n 分支名、L0i 依赖已发布 |
| L1a–L1e | pass | `test_package` 真实执行且实质依赖被测产物 |
| L2 | skip | CI 用 `--version`/`--help` 探测；medusa 只有 `-V`（版本），`-h` 是 host 参数，无 `--help`。可用性由 test_package 的 `medusa -d` 覆盖（22 个模块） |
| L4 | warn | 补丁文本含 `pthread_cancel`（0005 的非 OHOS 分支）与 `mktemp`（0004），非新增危险调用 |
| L5 | pass | `bin/` 有内容（`bin/medusa`） |

## 8. 测试断言（`assertion_count: 17`）

### 8.1 产物层 `test_medusa.sh`（10 条）

口径说明：上游 `src/listModules.c` 对 **dlopen 成功**、**dlopen 失败**
（`Couldn't load "…"`）与 **dlsym 失败**（`Invalid module … [no export of summaryUsage()]`）
三种结果打印的行首形状完全相同，因此脚本先显式剔除两类失败行再做统计，
"模块数"即真正的 dlopen 成功数（这一点在实现中已收紧，见脚本注释）。

1. `bin/medusa` 存在且可执行；
2. `lib/medusa/modules/*.mod` 已随包安装；
3. `medusa -d` 正常退出（未因 provider 加载失败而 ERR_FATAL）；
4. **dlopen 成功**的模块数 ≥ 10（实测 22；失败行已剔除，失败时另打印 `[warn]` 清单）；
5. `http` 模块加载；
6. `ftp` 模块加载；
7. `smtp` 模块加载；
8. `telnet`/`vnc` 模块加载；
9. `ssh` 模块加载（libssh2 + libgcrypt 集成成功）；
10. 诊断项：核心动态符号表 `EVP_*` 数量、`OPENSSL_MODULES` 内容、模块目录内容。

### 8.2 消费者层 `test_medusa_e2e.sh`（7 条，完整消费者用例）

真机实测的完整流程：`ftp_e2e_server.py` 在 127.0.0.1 随机端口上以**唯一合法口令**
（`e2euser` / `e2epass`）提供服务 → 包内 `medusa -M ftp -h 127.0.0.1 -n <port> -u … -p …`
发起真实审计 → 命中口令 → 再用 `wrongpass` 做反向对照。断言如下：

11. 正向：FTP 服务收到 `USER e2euser`（wire log `E2E USER e2euser`）；
12. 正向：FTP 服务收到 `PASS`（wire log `E2E PASS …`）；
13. 正向：服务端确认该口令通过认证（wire log `E2E AUTH_OK`）；
14. 正向：medusa 输出 `ACCOUNT FOUND: [ftp] Host: 127.0.0.1 User: e2euser Password: e2epass [SUCCESS]`；
15. 反向：错误口令下 medusa **不得**出现 `[SUCCESS]` 行；
16. 反向：错误口令下服务端 **不得**出现 `E2E AUTH_OK`，且必须确实收到过 `E2E PASS wrongpass`（证明对话真的发生，而非静默跳过）；
17. 两次运行的输出中均不得出现 `FATAL:` / `Error loading OpenSSL`。

真机实测结果（`E2E` 全绿）

```text
2026-09-30 18:57:54 ACCOUNT CHECK: [ftp] Host: 127.0.0.1 (1 of 1, 0 complete) User: e2euser (1 of 1, 0 complete) Password: e2epass (1 of 1 complete)
2026-09-30 18:57:54 ACCOUNT FOUND: [ftp] Host: 127.0.0.1 User: e2euser Password: e2epass [SUCCESS]
[ok] server received the USER command
[ok] server received the PASS command
[ok] live FTP service authenticated the credential pair
[ok] medusa reported the audited credential as found
[ok] wrong password was transmitted and rejected; no false positive
[ok] no fatal errors in either run
ALL MEDUSA E2E TESTS PASSED
```

该脚本自身的判定能力也用两个**故意做坏的消费者**验证过（均被正确拒绝）：
一个无论服务端是否拒绝都打印 `SUCCESS`，一个不连服务端直接打印 `SUCCESS`；
而一个忠实模拟 ftp 模块对话的替身则被正确接受（正向对照）。

## 9. 结果结论

**真机编译、打包、测试全部通过**，无阻塞项。剩余可选项：

- `with_smb2`（libsmb2 的 SMBv2/3）默认关闭，需单独确认头文件布局后可开启；
- RDP/AFP/NCP/PostgreSQL/SVN 模块无 OHOS 依赖，保持裁剪。

交付前建议按 `ci/conan/build_and_test.sh archives/m/medusa/2.3` 再跑一次 shadow CI 作为最终门禁。
