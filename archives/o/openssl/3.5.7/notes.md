# openssl 3.5.7 适配笔记

## 编译环境
- 构建系统: OpenSSL 自有 perl `Configure` + make（非 autotools、非 cmake）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，真机 `~/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin/clang`）
- 目标平台: HarmonyOS PC aarch64（`linux-aarch64` target，profile `ohos-aarch64`）
- 任务: #6689（领取 2026-09-19），分支 `feat/openssl-3.5.7`
- 状态: built（真机 `conan create` 退出码 0 共三轮；推送的配方跑 116 脚本清单，全量 345 脚本另实跑两轮留证）

## 上游坐标

- tag `openssl-3.5.7` → `https://github.com/openssl/openssl/releases/download/openssl-3.5.7/openssl-3.5.7.tar.gz`
- 同文件亦发布于 `https://www.openssl.org/source/openssl-3.5.7.tar.gz`
- SHA-256 `a8c0d28a529ca480f9f36cf5792e2cd21984552a3c8e4aa11a24aa31aeac98e8`
  （本机下载后 `sha256sum` 与官方 `openssl-3.5.7.tar.gz.sha256` 逐字符一致，两入口字节相同）
- 运行时版本自证：消费者测试打印 `OpenSSL version: OpenSSL 3.5.7  9 Jun 2026`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 真机 `conan create` 卡在 `source()`：`Name does not resolve`（github.com / www.openssl.org 全失败） | 该时段真机 DNS/整网不可达，非配方问题（`codeload.github.com` 同刻可通） | 不改配方里的官方 URL；用 `core.sources:download_cache=<dir>` 预置 `<dir>/s/<sha256>` 跳过网络。该 conf **只能写在 `global.conf`**，`-c`/`-c:a`/profile 一律拒绝 `core.*`（报 `Bad conf definition`），故本次用独立 `CONAN_HOME` 承载，避免污染真机共享配置 |
| 2 | `OpenSSL 3.5.x` Configure 默认写 `CC=gcc` | 真机/CI 只有 clang | build() 从 profile `tools.build:compiler_executables` 取 CC 显式传入（R33），OHOS 下追加 `-D__MUSL__` |
| 3 | 链接期 lld 报找不到 `libxml2.so.16` | SDK 的 lld 依赖 llvm/lib 下的 libxml2 | 沿用 3.5.8.1 的 `LD_LIBRARY_PATH=<sdk>/lib:<sdk>/sysroot/usr/lib:${LD_LIBRARY_PATH:-}` 注入（build 与 test_package 两处） |
| 4 | musl 无 glibc 私有符号 `__fd_chk` | OHOS libc 不提供 | 复用 0002 补丁提供有界 `openssl_fdset`（`-D__MUSL__` 激活）+ 0001 让 `apps/speed.c` 走该 helper。**3.5.7 与 3.5.8 两处上下文完全一致，补丁零改动复用**（`git apply --check -p1` 与 conan `Apply patch (portability)` 均干净） |
| 5 | `make install` 生成文档失败（缺 pod.in） | 3.5.x 源码树缺部分 man 源 | 沿用 `make install_sw`（只装软件） |
| 6 | 上一版配方（3.5.8.1）把「`make test` 跑到 130 个文件超时截断」当成通过 | 不满足 §3.4/§3.7 | 本版 build() 内真实执行上游 harness：`make build_sw -j2` → `HARNESS_JOBS=4 timeout 1500 make test TESTS="<116 个安全关键脚本>"`，失败即非零退出、不吞异常；全量 345 脚本另在真机实跑两轮留证（见下） |

## 构建与测试实测耗时（真机 8 核，`-j2` + `HARNESS_JOBS=4`）

```
START 2026-09-19 13:31:29        # conan create 开始
libssl.a / libcrypto.a           13:43:16 / 13:43:31   # make build_sw ≈ 12 min
apps/openssl                     13:45:25             # build_sw 完成 ≈ 14 min
make test (harness 汇总)         Files=344, Tests=4024, 930 wallclock secs, Result: PASS
END   2026-09-19 14:01:30        CREATE_EXIT:0        # 全程 30 min 01 s
```

第 2 轮（清掉包缓存后重跑，15:25:07 → 16:00:47，CREATE_EXIT:0，35 min 40 s）同一份最终字节
再出 `Files=344, Tests=4024, 1144 wallclock secs, Result: PASS` —— 同一套件两轮相差 23%，
说明全量在 CI 侧没有余量。清单成本：`make test TESTS="<116 个脚本>"` 单独实测
`Files=116, Tests=3085, 665 wallclock secs, Result: PASS`（16:15:24 → 16:26:34，RC=0）。

第 3 轮（16:40:26 → 17:09:28，CREATE_EXIT:0，29 min 02 s）＝ **最终推上去的那份配方**，
`build()` 内执行 116 脚本清单：`Files=116, Tests=3086, 736 wallclock secs, Result: PASS`，
`not ok` 0 条，116 个 `.t` 全部 ok，消费者 `=== Results: 12/12 tests passed ===`。

### 为什么 build() 跑 116 个脚本而不是全量 345

CI 单包预算 3600 s（`ci/config/build_timeouts.txt` 无 openssl 条目，rule5 又禁止贡献者改 `ci/`）。
全量 harness 单独就要 930～1144 s，且 `make test` 会先构建全部 248 个测试程序
（Makefile：`test: tests → _tests: build_programs`），叠加 worker 编译速度未知，全量没有余量。
116 个脚本覆盖加密算法 / ASN.1 / X.509 / PKCS / TLS / QUIC / provider 主线，真机 3085 子用例全通过；
配方用 `timeout 1500` 给这步加硬失败护栏（不吞异常：harness 失败或超预算都让 create 非零退出）。
全量 4024 用例 100% PASS 的结果保留在 `reports/test-report.md`，作为上游覆盖度证据。

### CI 首轮失败的真正原因（`conandata.yml` 的 url 形态）

第 1 次 CI（构建 #51166，SHA `0c727e00`）报 `conan create TIMED OUT after 3600s`，自动诊断归因为
「网络问题 / 源码下载超时」。核对整份日志后确认根因在配方写法：

- `sources.url` 当时写成 list；CI 的镜像注入 `replace_url()` 只匹配单值形态
  （正则 `^(\s*)url:\s*(["'])(https?://...)\2\s*$`，脚本注释明写「不处理已经是列表的」），
  list 形态等于**关掉了 CI 的镜像注入**；
- 该 worker 上没有 `curl`（日志里 `[Errno 2] No such file or directory: 'curl'` 反复出现），
  预下载兜底同样失效；
- 于是 conan 直连 github.com 拉 53 MB，固定断在 20 MiB：
  `IncompleteRead(20971520 bytes read, 32182410 more expected)`，重试到 3600 s 用尽；
  日志中 `Configuring OpenSSL` / `build_sw` 出现 0 次 —— **根本没进入编译**。

修复 = `sources.url` 用单值官方地址，由 CI 自动展开镜像（本仓已发布的 3.5.6 / 3.5.6.1.x / 4.0.1
都是这个形态）。另一个坑顺带记下：`conandata.yml` 的**注释里不要写带 `://` 的地址**，
CI 是按整行正则扫全文抓 URL 的，我之前在注释里写的 `...tar.gz.sha256` 被当成一个源码 URL 去预下载了。

## 上游测试台账

| 口径 | 数量 | 取数命令 |
|---|---|---|
| 测试脚本（`.t`，harness 调度的用例文件） | 345 | `ls test/recipes/*.t \| wc -l` |
| 其中本次实跑并全通过 | 297（48 skipped + 297 ok = 345；日志 `not ok` 0 条） | 真机日志 `grep -cE "\.t \.+ ok$" ` |
| 其中按构建配置自跳过 | 48（逐条原因见 `reports/test-report.md`） | `grep -oE "^[0-9]+-.*\.t \.+ skipped: .*" 日志 \| sort -u` |
| TAP 子用例（harness 自报） | **4024** | 日志尾 `Files=344, Tests=4024 ... Result: PASS` |
| C 测试程序 | 248 | `grep -oE 'SOURCE\[[^]]+\]' test/build.info \| sort -u \| wc -l` |
| C 程序内 `ADD_TEST` 注册的子用例 | 1041 | `grep -rhoE '\bADD_TEST\(' test/*.c \| wc -l` |
| `evp_test` KAT stanza 数据文件 | 107 | `ls test/recipes/30-test_evp_data/*.txt \| wc -l` |

对外声明的用例数取各口径最大值 **4024**（harness 自报），声明值 ≥ 任何静态 grep 口径，不存在少报。

48 个 skipped 全部由上游自身按构建配置判定，非本地禁用，按原因归类：

| 原因 | 个数 | 说明 |
|---|---|---|
| needs the dynamic engine feature enabled | 25 | R26 要求 `no-shared`（libssl/libcrypto 与系统 `/lib` 同名冲突），dynamic engine 依赖可动态加载的引擎；这批只做 TLS 报文级探测，握手/算法主覆盖由实跑并通过的 `80-test_ssl_new.t`、`90-test_sslapi.t`、`80-test_dtls_mtu.t`、`30-test_evp_pkey_provided.t` 等承担（真机日志逐条 ok） |
| No external tests in this configuration | 7 | 需 krb5 / pyca-cryptography / cloudflare-quiche / gost-engine / oqsprovider / pkcs11-provider / tlsfuzzer 等第三方外部套件，非 OpenSSL 自身构建产物 |
| fips build only | 6 | 未启用 `enable-fips`（fipsinstall / fipsmodule_cnf / pairwise / cli_fips / fipsload） |
| enable-tfo | 2 | TCP Fast Open 未 `enable-tfo` |
| certificate/ bio compression disabled | 2 | 未启用压缩算法（`no-comp` 语义） |
| rc5 not supported / ACVP not supported / SSLKEYLOGFILE / shared build only / tls13secrets / windows registry | 6 | 分别对应未启用 RC2/RC5 legacy 提供器、未 `enable-acvp-tests`、未 `enable-ssl-key-log-file`、`no-shared`、未 `enable-tls1_3_secrets`、Windows 专属 |

## 交付物

| 文件 | 说明 |
|---|---|
| `archives/o/openssl/3.5.7/conanfile.py` | 配方：Configure + `make build_sw` + `timeout 1500 make test TESTS="<116 脚本>"`（真实执行上游 harness，失败即非零退出） |
| `archives/o/openssl/3.5.7/conandata.yml` | `sources.url` 写成**单值**官方 github release 地址（CI 镜像注入只认单值），patches 为 list 格式（L0f）；注释中不出现 `://` |
| `archives/o/openssl/3.5.7/patches/0001`、`0002` | musl 有界 fd_set（复用，零改动） |
| `archives/o/openssl/3.5.7/test_package/` | L1 消费者测试 12 断言 + `MANIFEST.yml`（`upstream_test_in_build: true`） |
| `archives/o/openssl/3.5.7/reports/test-report.md` | 真机全量测试证据（含 48 条 skipped 明细） |
| `archives/o/openssl/manifest.yaml`、`commands.json` | 库级登记新版本（L0k 要求 commands.json 含本版本号） |

## 注意事项

- 产物含 `bin/openssl`（CLI）→ 软件级 `commands.json` 必须含 `3.5.7` 条目（L0k/R38），已补
- 静态包：`libcrypto.a` + `libssl.a`（R26 no-shared），`package_info` 给 `libs=[ssl, crypto]`、`system_libs=[dl, pthread]`
- 无 Conan 依赖（`requirements()` 显式留空：不启用 zlib 压缩路径），因此 L0i/R36 无待发布依赖
- 熵源：`--with-rand-seed=getrandom`（OHOS musl 无 `/dev/*random` 旧探测路径）
