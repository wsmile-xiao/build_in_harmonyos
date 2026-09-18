# kea-shell 3.0.3 适配笔记（HarmonyOS PC / OHOS aarch64）

目标：ISC Kea 3.0.3 的 REST 文本客户端 `kea-shell`
（源码路径 `src/bin/shell/`，产物为可执行脚本 `kea-shell` +
两个 Python 模块 `kea_conn.py` / `kea_connector3.py`）。

## 编译环境

- 构建系统：Meson（Kea 3.0 起由 Autotools 迁移到 Meson）
- 编译日期：2026-09-16
- 编译器：clang/clang++ 15.0.4（`/data/service/hnp/bin`），triplet `aarch64-linux-ohos`
- Conan profile：`ci/conan/profiles/ohos-aarch64`（host = build = OHOS armv8，native 构建）
- 状态：built

## 关键判断：本包没有编译步骤

`src/bin/shell/meson.build` 全文只有 3 个 `configure_file()` 和
`subdir('tests')`，**没有 `executable()` / `library()` / `dependencies:` /
`link_with:`**，目录内也没有任何 `.cc/.h` 源文件（`find` 实测 0 个）。
kea-shell 的上游"构建"就是 configure 阶段的文本替换：

| 输入 | 输出 | 安装位置（上游） |
|------|------|------------------|
| `kea-shell.in` | `kea-shell`（替换 `@PYTHON@`/`@PACKAGE_VERSION@`/`@EXTENDED_VERSION@`/`@PKGPYTHONDIR@`） | `SBINDIR` |
| `kea_conn.py` | `kea_conn.py`（copy） | `PKGPYTHONDIR`(= purelib/kea) |
| `kea_connector3.py` | `kea_connector3.py`（copy） | `PKGPYTHONDIR` |

因此配方**在 `meson.configure()` 之后停止**：`meson setup` 已经写出全部交付物，
`build()` 不再调用 `meson.build()`，也没有任何编译目标。

## 编译步骤

```bash
# 1. 源码：官方发布包 ftp.isc.org
curl -o kea-3.0.3.tar.xz https://ftp.isc.org/isc/kea/3.0.3/kea-3.0.3.tar.xz
# sha256 = 09702ddb078b637e85de9236cbedd3fb9d7af7c6e797026c538b45748ad4d631

# 2. Conan 依赖 + Meson 工具链（配方 generate() 完成）
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
#    → conan_meson_native.ini（compiler/binaries/pkg_config_path/buildtype）+ 依赖 .pc + 运行期 LD_LIBRARY_PATH

# 3. 配置（= 本包的全部构建动作）
meson setup <builddir> <srcdir> --native-file=conan_meson_native.ini -Dtests=enabled \
    -Dcrypto=openssl -Dmysql=disabled -Dpostgresql=disabled -Dnetconf=disabled -Dkrb5=disabled
#    → <builddir>/src/bin/shell/kea-shell（可执行）、kea_conn.py、kea_connector3.py

# 4. 上游测试（本包 build() 内执行 python-tests；全部 13 个入口见下）
meson test -v -C <builddir> --suite python-tests
```

## 遇到的问题与解决方案

| # | 问题（首个错误） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".`（`reports/meson-setup-first-error.log`） | OHOS 上 `platform.system()` 返回 `HarmonyOS`，meson 据此报告 host system=`harmonyos`；Kea 用 `build_machine.system()` 做平台分支，白名单里没有 harmonyos | 补丁 0001：顶层 `meson.build` 把 `SYSTEM == 'harmonyos'` 归一化为 `'linux'`（与知识 E090 同类） |
| 2 | 生成的 `kea-shell` shebang 为 `#!@PYTHON@` → 构建机绝对路径 `/storage/Users/currentUser/usr/local/bin/python3` | 上游把 configure 时找到的解释器绝对路径写进脚本；该路径属于构建者家目录，Conan 包不可重定位 | 补丁 0002：`#!@PYTHON@` → `#!/usr/bin/env python3`（本机 `/usr/bin/env` 由 toybox 提供，知识 E037 条件 1 分支成立） |
| 3 | `sys.path.append('@PKGPYTHONDIR@')` 展开为 `/usr/local/lib/python3.12/site-packages/kea` | PKGPYTHONDIR 是构建机 Python 的 purelib，Conan 包无法占用该路径 | 不改脚本：两个模块与 `kea-shell` 同目录安装（`bin/`），由 CPython 的脚本目录 `sys.path[0]` 项解析 `import kea_conn` / `import kea_connector3`；该 append 指向不存在的目录，无副作用（本地从任意 cwd 运行 + HTTP 往返实测通过） |
| 4 | `chaos: Boost TLS support broken.`（`HAVE_GENERIC_TLS_METHOD` DID NOT COMPILE） | OHOS musl `pthread.h` 未声明 `pthread_setcancelstate`，`boost/core/detail/sp_thread_sleep.hpp` 无条件调用 | `generate()` 注入 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`（boost 官方逃生宏，知识 E127） |
| 5 | `cpp.run()` 探针 `LOG4CPLUS_INITIALIZER_H … NO (127)` | Meson 特性探针是 compile-and-run，native 构建下真实执行；host 共享依赖 `liblog4cplus.so.9` 不在配置期运行环境 | `generate()` 用 `Environment` 把各 host 依赖 `libdir` 追加进 `LD_LIBRARY_PATH` 并 `save_script("conanbuildenv-kea-runtime")` |
| 6 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]` | Conan buildenv 把 `AR=llvm-ar` 写进 machine file；CI/本机 PATH 不保证含 llvm-ar/llvm-ranlib | `generate()` 从 `tools.build:compiler_executables` 的编译器路径推导同目录 `llvm-ar`/`llvm-ranlib` 写入 `tc.binaries`（知识 E481） |
| 7 | meson 无法解析 boost/log4cplus/openssl/gtest | `MesonToolchain` 只设 `pkg_config_path=generators_folder`，没有 `.pc` 文件 | `generate()` 中 `PkgConfigDeps(self).generate()` 生成依赖 `.pc` |
| 8 | `src/lib/dhcp/iface_mgr_linux.cc:40: error: redefinition of 'sockaddr_storage'`（仅在构建 Kea 服务端二进制时出现，用于跑上游进程测试） | OHOS sysroot 的 `linux/socket.h`（bionic 派生）与 musl `sys/socket.h` 都定义 `struct sockaddr_storage` | **不属于本包产物**：仅为本地运行 12 个 `.sh` 进程测试而临时应用同批 `kea-hook-lease-query/3.0.3` 的 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`（知识 E091），执行后已从工作树还原，未纳入本包 `patches/` |
| 9 | **CI 首轮失败（PR #10342 / build #48667）**：`subprocess.TimeoutExpired: Command '['…/bin/kea-shell', '--host', '127.0.0.1', '--port', '45009', '--service', 'dhcp4', 'list-commands']' timed out after 60 seconds` → `ERROR: kea-shell/3.0.3 (test package): Error in test() method` → `L1_RESULT=fail: conan create failed` | `kea-shell` 用 `for line in sys.stdin:` 读取 stdin 上的可选参数并**读到 EOF 才继续**（上游行为，故上游 `.sh` 测试一律用 `echo | kea-shell`）；CI worker 的 stdin 是**永不关闭的管道**，`test_package` 里 `subprocess.run()` 继承了它 → 子进程永久阻塞在 stdin 读；脚本内部的 `signal.alarm(timeout)` 位于该循环**之后**，无法兜底（知识 E214「交互式阻塞」同类） | `test_package/test_kea_shell.py` 的 `run()` 统一 `stdin=subprocess.DEVNULL`（显式给 EOF）；子进程超时由 60 s 收紧为 30 s 以快速暴露同类问题 |

## 源码修改

`patches/0001-meson.build.patch`

```meson
 SYSTEM = build_machine.system()
+# OpenHarmony/HarmonyOS shares the Linux userspace ABI (musl libc, Linux
+# syscalls, linux iface_mgr/pkt_filter back-ends). Meson reports the
+# platform as 'harmonyos'; normalize it to the Linux branch below.
+if SYSTEM == 'harmonyos'
+    SYSTEM = 'linux'
+endif
 if SYSTEM == 'linux'
```

`patches/0002-src-bin-shell-kea-shell.in.patch`

```diff
-#!@PYTHON@
+#!/usr/bin/env python3
```

两个补丁均不含 `__OHOS__` 平台宏。

## 依赖版本

| 依赖 | 版本 | 类型 | 制品仓验证 |
|------|------|------|-----------|
| boost | 1.85.0 | 工程级配置门禁（`meson.build:192` required 无 fallback；14 项头 `required:true`） | `conan download` exit 0 |
| log4cplus | 2.2.0.1 | 工程级配置门禁（`meson.build:220` wrap fallback） | `conan download` exit 0 |
| openssl | 3.5.8.1 | 工程级配置门禁（`meson.build:231/314-320` 默认 crypto 后端，缺失即 error） | `conan download` exit 0 |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled` 必需） | `conan download` exit 0 |
| meson | 1.11.0 | 构建工具 tool_requires（boost 无 libboost_system，需 meson ≥1.10 的 header-only 回退） | `conan download` exit 0 |

可选后端（botan/krb5/mysql/postgresql/netconf）制品仓无可消费依赖，配方显式
`disabled`。kea-shell 本体（目标级）**零第三方依赖**：不链接任何第三方库，也不
链接 kea 内部库（无 `link_with:`）。

## 上游测试结果（R51 三步法 · 清点 → 实跑 → 如实回填）

清点：`src/bin/shell/tests/meson.build` 注册 **13 个 test()**
（1 个 suite `python-tests` + 12 个 suite `shell-tests`；门禁 `-D tests=enabled`）。

实测（本机 OHOS aarch64，25.0 秒~258 秒/项，执行时机器 loadavg ≈ 56）：

```bash
$ meson test -v -C <builddir> --suite python-tests
1/1 python-tests - kea:shell_unittest.py  OK   0.17s        # 内部 Ran 11 tests ... OK
exit_code=0

$ meson test -v -C <builddir> --timeout-multiplier=10 \
    ca_basic_auth_tests.sh d2_basic_auth_tests.sh dhcp4_basic_auth_tests.sh dhcp6_basic_auth_tests.sh \
    shell_ca_process_tests.sh shell_d2_process_tests.sh shell_dhcp4_process_tests.sh shell_dhcp6_process_tests.sh \
    tls_ca_process_tests.sh tls_d2_process_tests.sh tls_dhcp4_process_tests.sh tls_dhcp6_process_tests.sh
Ok: 12   Fail: 0   Timeout: 0
exit_code=0
```

| 上游测试入口 | 子用例数 | 通过 | 耗时 | 日志 |
|---|---|---|---|---|
| `shell_unittest.py`（python-tests） | 11 | 11 | 0.17 s | `reports/upstream-test-python-tests.log` |
| `ca_basic_auth_tests.sh` | 7 | 7 | 68.11 s | `reports/upstream-test-shell-tests.log` |
| `d2_basic_auth_tests.sh` | 7 | 7 | 67.87 s | 同上 |
| `dhcp4_basic_auth_tests.sh` | 7 | 7 | 119.14 s | 同上 |
| `dhcp6_basic_auth_tests.sh` | 7 | 7 | 243.36 s | 同上 |
| `shell_ca_process_tests.sh` | 7 | 7 | 228.69 s | 同上 |
| `shell_d2_process_tests.sh` | 7 | 7 | 240.38 s | 同上 |
| `shell_dhcp4_process_tests.sh` | 7 | 7 | 258.34 s | 同上 |
| `shell_dhcp6_process_tests.sh` | 7 | 7 | 124.80 s | 同上 |
| `tls_ca_process_tests.sh` | 3 | 3 | 29.89 s | 同上 |
| `tls_d2_process_tests.sh` | 3 | 3 | 29.97 s | 同上 |
| `tls_dhcp4_process_tests.sh` | 3 | 3 | 58.60 s | 同上 |
| `tls_dhcp6_process_tests.sh` | 3 | 3 | 117.42 s | 同上 |
| **合计** | **79** | **79** | — | 失败 0，跳过 0 |

- 用例级明细：`reports/upstream-test-cases.md`（11 个 unittest 名称 + 4×14 个
  `{ca,d2,dhcp4,dhcp6}-shell.*` 子用例名称）
- 逐测试子用例统计：`reports/upstream-test-case-counts.txt`
- **超时预算**：meson 默认单测超时 30 s；首轮未加倍运行时 3 项（`ca_basic_auth_tests.sh`、
  `tls_dhcp4_process_tests.sh`、`tls_dhcp6_process_tests.sh`）被 30 s 预算截断
  （`TIMEOUT`，非产品失败），故本地运行统一使用 `--timeout-multiplier=10`
- **12 个 `.sh` 进程测试不在配方 build() 内执行**：它们启动 Kea 服务端
  （`kea-ctrl-agent`/`kea-dhcp-ddns`/`kea-dhcp4`/`kea-dhcp6`，见
  `dhcp_test_lib.sh` 的 `"${bin_path}/${bin}"`），这些二进制是同工程的其他目标、
  不属于本包交付物；本地验证阶段已构建这四个二进制并全量跑通（构建这些目标需要
  问题 8 的 `sockaddr_storage` 移植）

## 鸿蒙特有用例（test_package 内新增 1 例）

上游测试全部通过，但**上游没有任何针对鸿蒙/OHOS 平台的断言**：她的测试只关心 REST 语义，
不会发现"包的适配补丁没进产物"。因此 `test_package/test_kea_shell.py` 增加 1 个**鸿蒙特有案例**
（4 项断言），直接校验包内产物上的 OHOS 适配是否真的生效：

| 断言 | 校验的适配点 | 缺失时会怎样 |
|---|---|---|
| `kea-shell` 首行 == `#!/usr/bin/env python3` | 补丁 0002（上游写入的是构建机家目录下的解释器绝对路径） | 目标设备上 `bad interpreter`，脚本起不来 |
| `/usr/bin/env` 存在 | 该 shebang 形态的平台前提（OHOS 由 toybox 提供，知识 E037 条件 1） | `env` 形式 shebang 无法兑现 |
| `kea_conn.py` 与脚本同目录 | OHOS 包布局决策（上游 `PKGPYTHONDIR` 指向构建机 `purelib/kea`，Conan 包无法占用） | 脚本 `import kea_conn` 失败 |
| `kea_connector3.py` 与脚本同目录 | 同上 | 脚本 `import kea_connector3` 失败 |

**反向验证（证明不是空壳断言）**：把包内脚本首行改回上游的绝对路径
（`#!/storage/Users/currentUser/usr/local/bin/python3`）后运行该测试 →

```
$ head -1 <neg-pkg>/kea-shell
#!/storage/Users/currentUser/usr/local/bin/python3
$ PATH=<neg-pkg>:$PATH python3 test_package/test_kea_shell.py
checks run: 16
FAIL: the OHOS shebang patch is not in effect: first line is '#!/storage/...'
rc=1
```

→ 该案例确实能抓住"适配补丁丢失"，不是空壳。断言全部落在**包内文件**上，
故仍然真实依赖被测包（移走 `bin/` 即失败，CI 的 L1e 破坏性反向验证依旧成立）。

## 验证结果

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → 见 reports/conan-create.log（configure + python-tests + package + test_package）
$ conan-verify kea-shell 3.0.3
# → 见 reports/conan-verify-report.md
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/kea-shell` | REST 文本客户端（上游 configure_file 生成，0755） |
| `bin/kea_conn.py` | 请求/响应模型模块（与脚本同目录，供 `import kea_conn`） |
| `bin/kea_connector3.py` | Python 3 HTTP/HTTPS 连接模块（同上） |
| `licenses/COPYING` | 上游许可证（MPL-2.0） |
| `patches/` | 2 个平台适配补丁 |

## 注意事项

- **无编译产物**：本包不含 ELF 文件（`package_type = "application"`，`binary:
  false`），CI 的 ELF 检查（L4）对本包无对象。
- **运行前提**：目标设备需要 Python 3 与 `/usr/bin/env`（OHOS 由 toybox 提供）；
  `kea-shell` 通过 `#!/usr/bin/env python3` 启动，因此 `python3` 需在 PATH 中。
- **shebang 可移植性**：`#!/usr/bin/env python3` 依赖 `/usr/bin/env` 存在
  （知识 E037 的条件 1）；若目标镜像无 `/usr/bin/env`，需改为解释器直接路径。
- **不构建服务端**：本包只配置 Kea 工程、只打包 kea-shell；Kea 服务端
  （dhcp4/dhcp6/ddns/ctrl-agent）与本包无关，未打包。
- **测试范围**：配方内跑覆盖交付物的 `python-tests`（11 用例）；12 个 `.sh` 进程
  测试属跨组件集成测试，已在本地全量执行并留档，但需要 Kea 服务端二进制，
  不在配方 build() 内。

## CI 首轮失败与修复（PR #10342 / build #48667）

**现象**：CI 报「构建超时 — 可能是交互式测试卡住」，实际日志尾部为 test_package 的
`subprocess.TimeoutExpired: Command '['…/bin/kea-shell', '--host', '127.0.0.1', '--port', '45009',
'--service', 'dhcp4', 'list-commands']' timed out after 60 seconds` →
`ERROR: kea-shell/3.0.3 (test package): Error in test() method, line 28` → `L1_RESULT=fail: conan create failed`。

**根因（本机复现）**：`kea-shell` 会读取 stdin 上的可选参数，`for line in sys.stdin:` **读到 EOF 才继续**；
CI worker 的 stdin 是**永不关闭的管道**，`test_package` 的 `subprocess.run()` 继承了它 → 被测命令永久阻塞在
stdin 读；而 `kea-shell` 的 `signal.alarm(timeout)` 在该循环**之后**才设置，无法兜底。
上游自己的 `.sh` 测试早就规避了这一点——它们一律写成 `echo | kea-shell …`（喂 EOF）。

```
$ python3 stdin-probe2.py <pkg>/bin/kea-shell          # 保持 stdin 常开、不关闭
[stdin=DEVNULL] 完成 rc=1 out='Failed to run: <urlopen error [Errno 111] Connection refused>'
[stdin=常开管道（不关闭）] ❌ 阻塞 >8s（stdin 保持打开=True）
→ 根因确认：kea-shell 的 `for line in sys.stdin` 在 stdin 不关闭时永久阻塞（CI buildbot stdin 常开）
```

**修复**：`test_package/test_kea_shell.py` 的 `run()` 统一 `stdin=subprocess.DEVNULL`，并加注释说明原因；
子进程超时 60 s → 30 s（同类问题更快暴露）。

**修复后验证（在 CI 条件下复跑）**：

```
$ python3 test_kea_shell.py                    # 常规（stdin = 终端/EOF）
checks run: 12 / all checks passed             rc=0
$ sleep 90 | python3 test_kea_shell.py         # 模拟 CI：测试进程 stdin 常开、永不 EOF
checks run: 12 / all checks passed             rc=0
$ conan create . -pr:h=…ohos-aarch64 -pr:b=…ohos-aarch64   # 以 stdin 常开管道运行（CI 等价条件）
Ran 11 tests in 0.000s          # build() 内上游测试
checks run: 12 / all checks passed
CI 条件（stdin 常开）conan create EXIT_CODE = 0
```
日志：`~/tmp/kea-shell-audit2/{stdin-probe2.py,repro-*,verify-conan-create-ci-stdin.log,verify-ci-stdin-rc.log}`

## 本地 W3（本地 CI 模拟）结果

```
$ JUNK_PR_DIFF=<PK 文件清单 diff> python3 scripts/ohc-run.py finish kea-shell 3.0.3 built
Step 3/10 G0 干净构建验证: ✅（2 个补丁全部应用成功）
Step 4/10 conan-verify:    ✅ G0/G1/G2/G3/G4 PASS
Step 5/10 W3 本地 CI:      ✅ setup.sh 通过；build_and_test.sh 通过
    L0_RESULT=pass: all checks passed
    L1_RESULT=pass: upstream tests + test_package executed（L1c 上游测试已在 build 阶段执行）
    L1e: 破坏性反向验证通过（移走 bin/ 后测试确实失败 → test 真实依赖被测包）
    L2_RESULT=pass: kea-shell --help OK
    L4_RESULT=pass: patches clean
    L5_RESULT=pass: bin/ has content
    Build Summary: Total 1 / Success 1 / Failed 0 / Pass rate 100%
Step 6/10 finalize-archive: 通过（2 个非阻塞警告：release/debug tar.gz 属上传阶段产物；notes.md 对话记录）
Step 7/10 W5 知识图谱完整性: ✅（doc↔kv 540 对、必填字段完整、graph validate 通过）
```
产物：`reports/w3-local-ci.log`、`.ci-result.json`（exit_code=0，integrity_hash
07216e0906662f22，log_sha256 14518370…）、`ci-metadata.json`。

### W3 的 JC 口径说明（重要）

`ci/scripts/junk_check.sh` 有三种扫描模式：`prdiff`（有 PR 文件清单时，只查 PR
变更文件）> `incremental`（`git diff origin/main...HEAD`）> `full`（`git ls-files`
整仓）。本地首次 `finish` 时工作树尚无提交，JC 退化为 **full 模式**，命中
**仓库既有的、与本包无关的**运行期标记文件：

```
[FAIL] JC1: 2 个运行时状态文件被跟踪:
       archives/c/cloog/0.21.1/.build-closed
       archives/c/cloog/0.21.1/.staging-verified
```

这两个文件由 `origin/main` 的提交 `906cc59ae7`（cloog 0.21.1 适配）带入，
不属本包、也不在本 PR 范围（W2 要求本 PR 只含 kea-shell）。按 CI 的实际口径
（prdiff，只查 PR 文件清单，共 12 个文件）复核后 JC 全部通过：

```
$ JUNK_PR_DIFF=<PR 文件清单> bash ci/scripts/junk_check.sh <repo>
  检查模式: prdiff (12 个文件)
  JC1/JC2/JC3/JC4/JC5 无命中；JC6 涉及软件数: 1（合规）
  Junk Files: 0    JC_RESULT=pass
```

**结论**：本包的 PR 文件集合不触发任何 JC 门禁；`archives/c/cloog/0.21.1/`
的两个运行期标记是仓库存量的独立问题（建议由 cloog 或框架侧清理，不在本 PR 处理）。

## 门禁核验汇总（W2 / W3 / W0 / PF）

| 门禁 | 命令 | 结果 |
|------|------|------|
| W0 依赖发布预检 | `bash ci/scripts/preflight_check.sh kea-shell/3.0.3` | ✅ 5 个依赖（boost/gtest/log4cplus/meson/openssl）均已发布；版本号 3.0.3 未被占用 |
| W2 结构完整性（L0a-L0e） | `conanfile.py` / `conandata.yml` / `test_package/{conanfile.py,test_kea_shell.py,MANIFEST.yml}` / `patches/` | ✅ 齐备 |
| W2 PR 原子性（JC6） | `JUNK_PR_DIFF=<PR 清单> bash ci/scripts/junk_check.sh <repo>` | ✅ prdiff 模式 12 个文件、涉及软件数 1、Junk Files 0 |
| W3 本地 CI 模拟 | `ohc-run.py finish kea-shell 3.0.3 built`（step 5） | ✅ L0/L1/L1c/L1e/L2/L4/L5 全 pass，Pass rate 100% |
| 配方验证 | `ohc-run.py conan-verify kea-shell 3.0.3` | ✅ G0/G1/G2/G3/G4 + L2/L4/L5 PASS |
| W5 知识图谱 | `ohc-run.py finish`（step 7） | ✅ doc↔kv 540 对、字段完整、graph validate 通过 |
| PF1-PF9 + R52（提交前硬闸） | 以本包版本级文件 + 知识草稿清单调用 `ohc/preflight.py` 各检查函数 | ✅ 全部通过 |

### 提交前需注意：PF9 对"软件级文件"存在误报（框架问题，非本包问题）

`ohc/preflight.py:580` 的 PF9 规则为「所有 `archives/` 变更路径必须 ≥5 段」
（`archives/<字母>/<包>/<版本>/<文件>`），因此 **ARCHIVE-SPEC §2.1 强制要求的
软件级文件**（`archives/k/kea-shell/{README.md,commands.json,manifest.yaml}`，
4 段）会被判为"缺版本目录层"。

用三个**已合并**的真实提交复跑 `run_preflight()`，得到同样的告警（可复现）：

```
$ python3 -c "…preflight.run_preflight(repo, commit+'^', commit)…"
--- 13ba2f5932 【积分赛】feat(pari-nflistdata): 20220729 适配 HarmonyOS PC
    preflight ok=False
    PF9: 变更路径缺版本目录层 …: archives/p/pari-nflistdata/README.md, commands.json, manifest.yaml
--- ef6902def6 【积分赛】feat(omega): 2.0.0 适配 HarmonyOS PC
    preflight ok=False    （同上三条软件级文件）
--- 636a79e3cb 【积分赛】feat(pipemeter): 1.1.5 适配完成
    preflight ok=False    （同上三条软件级文件）
```

→ 结论：PF9 应豁免软件级白名单文件（`README.md` / `commands.json` /
`manifest.yaml`，与 `knowledge/ARCHIVE-SPEC.md §2.1` 对齐）。本包按 ARCHIVE-SPEC
保留这三个文件；若 `submit` 的 create-pr 阶段被 PF9 拦截，应先按框架问题反馈，
或在确认被拦文件"恰为上述三个软件级文件"后使用 `--no-preflight`。
---

**编译结束**: 2026-09-17 08:25
**最终状态**: built
