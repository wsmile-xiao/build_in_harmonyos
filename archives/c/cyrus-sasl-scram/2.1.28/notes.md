# cyrus-sasl-scram 2.1.28 — OHOS PC 适配笔记

> 分支 `feat/cyrus-sasl-scram-2.1.28` ｜ 平台 HarmonyOS PC / OpenHarmony aarch64（clang 15.0.4）
> 源码 `cyrus-sasl-2.1.28.tar.gz` sha256 `7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c`

## 0. 本包定位

上游 cyrus-sasl 2.1.28 一棵源码树产出多个机制包。本包只提供 **SCRAM 家族**
（SCRAM-SHA-1/224/256/384/512，RFC 5802 / RFC 7677），静态构造成 `libsasl2.a`
（SCRAM 经 `lib/staticopen.h` 注册，无运行期 `SASL_PATH`/dlopen 依赖）。
与姊妹包的关系：`cyrus-sasl`/`cyrus-sasl-digestmd5`/`cyrus-sasl-crammd5`/`cyrus-sasl-ntlm`
同源同版本、不同机制闭包。

依赖：**openssl/3.5.6**（唯一第三方依赖；SCRAM 的 Hi()/HMAC/PBKDF2 走 OpenSSL EVP）。

---

## 1. 上游测试申报表（R51 三步法）

| 项 | 结论 | 证据 |
|---|---|---|
| tests/ 目录数 | 0（上游无独立测试目录） | `ls` 无 `tests/` |
| automake 注册数 | 0（无 `TESTS`/`check_PROGRAMS`/`check-local`） | `grep -rn "TESTS\s*=" Makefile.am */Makefile.am` → rc=1 |
| ctest/meson/pytest | 0 | `ls CMakeLists.txt meson.build pytest.ini` → rc=2 |
| 自包含断言测试台 | **1**：`utils/testsuite.c`（`utils/Makefile.am:49 EXTRA_PROGRAMS`），`main()` 19 个阶段 | `grep -n EXTRA_PROGRAMS utils/Makefile.am` |
| 实际执行 | ✅ 已执行（两个闭包 + 8 seed 矩阵 + 全部 5 个样例） | `reports/upstream-tests.md` |

**实测计数**：交付闭包（`--with-dblib=none`）下 testsuite 停在阶段 1（需口令库）；
独立 sasldb/LMDB 测试树中 **10/19 阶段通过、1 阶段失败**（阶段 11 `client-first/server-last`
的 SCRAM-SHA-256：`Failed with: sasl_server_start() error`，8/8 seed 稳定复现）、其余未到达；
17 次 `SCRAM-SHA-* --> successful result`（另有 EXTERNAL 3 次，`successful result` 合计 20 行，与
日志实测 `grep -c` 一致）。逐项读数与根因见 `reports/upstream-tests.md`。

---

## 2. 适配过程中的真实问题（首个错误 → 根因 → 修复 → 复验）

### P0 `--with-openssl` 生效前的编译器试探拿不到 libcrypto（conan create 首轮失败）

- **首个错误**（真实输出）：
  ```
  configure:3985: /data/service/hnp/bin/clang -fPIC -O2 ... -L/storage/Users/currentUser/usr/local/lib conftest.c -lcrypto
  ld.lld: error: unable to find library -lcrypto
  configure:4034: error: C compiler cannot create executables
  cyrus-sasl-scram/2.1.28: ERROR: ... Error in build() method, line 194
  ```
  rc=1（日志 `evidence/logs/40-conan-create.attempt1.log`，config.log 行 120-122）
- **根因**：recipe 用 `LIBS="-lcrypto"` 提供 SCRAM 静态闭包（上游 SCRAM 分支不会把
  `-lcrypto` 加进 `SASL_STATIC_LIBS`）。但 `LIBS` 从 configure 的**第一条**编译命令起就生效，
  而此时的 `LDFLAGS` 只有 `-L.../usr/local/lib`（AutotoolsToolchain 未带入 openssl 的 lib 目录），
  于是首轮 “whether the C compiler works” 试探直接失败。手工 `build_ohos.sh` 之所以能过，
  是因为它额外显式传了 `LDFLAGS="-L<openssl>/lib"`。
- **修复**（`conanfile.py::generate()`，最小改动）：把 openssl 路径显式并入工具链
  ```python
  _openssl_root = self._openssl_root()
  tc.extra_cflags.append("-I%s/include" % _openssl_root)
  tc.extra_ldflags.append("-L%s/lib" % _openssl_root)
  ```
  （注：`AutotoolsToolchain` 无 `extra_cppflags` 属性，include 走 `extra_cflags`；
  实测 `['cflags','cxxflags','defines','ldflags','rcflags']`。）
- **复验**：`conan create` rc=0（102s），configure 正常解析到 `libcrypto`。

### P1 test_package 断言过严（把合法的 gs2-authzid 判成不合规）

- **首个错误**：`FAIL: client-first not RFC 5802 shaped: n,a=scramuser,n=scramuser,r=N/od+jpDbXFGHDb2/LfdA5Jf1kt17rah`
- **根因**：RFC 5802 的 `gs2-header = gs2-cbind-flag "," [ "a=" authzid ] ","`，authzid 段合法可选。
  本测试的客户端回调同时提供 `SASL_CB_USER`，库因此填了 `a=scramuser`；测试却硬要求 `n,,`。
- **修复**：断言放宽为 `gs2-cbind-flag == "n"` + 必须含 `n=<authid>` + `,r=<nonce>`（nonce ≥16B）。
- **复验**：`conan create` rc=0，8/8 CHECK-OK + 鸿蒙静态断言通过。

### P2 上游 old-style C 样例的 OHOS 平台问题（非交付路径）

1. **`getpass(3)` 已从 musl 移除**：`sample/client.c:145` 等调用裸 `getpass`。仅跑样例时
   链接 `ohos-getpass-shim.c`（只补该 libc 入口，不改样例逻辑/断言）。
2. **`sample-client` 口令交互路径 SIGSEGV（rc=139）**：最小复现
   `printf 'S: U0NSQU0tU0hBLTE=\n1234\n' | ./sample/sample-client`；2/3/4 行输入均 rc=139
   （排除“输入耗尽”假说）。同库同静态配置下 `test_package`/`utils/testsuite` 的相同调用链正常，
   **定性为上游 demo 程序自身缺陷**；平台禁 ptrace（`gdb: ptrace: Permission denied`）暂无法取栈。
3. **`utils/smtptest` 需外部 SFIO**：`./smtptest.c:9:10: fatal error: 'sfio.h' file not found`
   （上游 `smtptest_SOURCES` 为空），本包与制品仓均无 sfio，无法构建。

### 既有（同源姊妹包已验证）的 OHOS 适配点

- `config.guess` 不识别 `uname -s=HarmonyOS` → 补丁 0002/0003；**禁止** `--build/--host` 覆盖。
- HMDFS 下 `umask 077` 造的 autoconf 临时目录属主不可写 → configure 改写为 `umask 022`。
- OHOS 只有 clang → 显式喂 `CC_FOR_BUILD`/`CPP_FOR_BUILD`。
- 静态构建 `linksrcs` 只做 symlink → 复制 `SASL_STATIC_SRCS`（scram.c / db_none.c）到 `lib/`。
- `utils/testsuite.c` 用 `char` 承接 `getopt()` 返回值在 aarch64 上截断失效 → 补丁 0001 改 `int`。

---

## 3. 鸿蒙相关改动清单

| 文件 | 内容 |
|---|---|
| `patches/0002-config-config.guess.patch` | HarmonyOS → `aarch64-unknown-linux-ohos` 三元组 |
| `patches/0003-config-config.sub.patch` | 接受 `linux-ohos` |
| `patches/0001-utils-testsuite.c.patch` | `getopt()` 返回值 `char`→`int`（OHOS aarch64 截断致测试台 0 执行） |
| `conanfile.py` | `settings.os in ("Linux","OHOS")` 校验；`CC_FOR_BUILD`/`CONFIG_SHELL`/可写 `TMPDIR` 注入；umask 022 改写；静态 linksrc 复制；`-L/-I<openssl>` 注入（见 P0）；静态-only 产物清理 |
| `test_package/test_scram.c` | **鸿蒙特有断言**：`SASL_PATH` 指向不存在目录时仍枚举出 SCRAM 全家族（证明静态链入、无 dlopen） |

---

## 4. 复现命令（本地真机）

```bash
# 构建（含 P0 修复后的配方路径）
cd <worktree>
conan create archives/c/cyrus-sasl-scram/2.1.28 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    '--build=cyrus-sasl-scram/*'

# 上游测试台（交付闭包）
make -C utils testsuite && SASL_PATH=<empty-dir> ./utils/testsuite -a -s 1

# 上游 testsuite 完整闭包（一次性 sasldb/LMDB 测试树）
sh evidence/phaseB_sasldb.sh

# 样例（全部）
sh evidence/upstream_tests_v2.sh
```
---

**编译结束**: 2026-09-26 11:30
**最终状态**: built
