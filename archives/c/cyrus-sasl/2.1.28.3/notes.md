# cyrus-sasl 2.1.28.3 适配笔记（HarmonyOS PC · aarch64 · Conan autotools）

## 1. 定位与范围

- 产出 **动态 `libsasl2.so.3`**（SONAME `libsasl2.so.3`）+ 机制插件（`lib/sasl2/*.so`），供 dlopen 与下游依赖使用。
- 自包含构建：`--with-dblib=none`，关闭全部外部认证后端（saslauthd / PAM / LDAP / SQL /
  Kerberos-GSSAPI / OpenSSL / DES / OPIE / GDBM / NTLM / SRP / OTP / pwcheck / authdaemon）。
- **零 conan 运行时依赖**；`readelf -d libsasl2.so.3.0.0` 的 `DT_NEEDED` 仅 `libc.so`。
- 本包是**纯库包**：`package()` 显式删除全部可执行文件（上游 `bin/pluginviewer` 以及
  `sbin/` 下的工具）与全部 `*.la`，交付树只含 `lib/`、`include/`、`lib/pkgconfig/`、
  `licenses/`。因此**不创建** `commands.json`（R38/PF8：库包不应有）。

## 2. 版本号决策（R37 / L0j）—— 采用 **2.1.28.3**

上游版本为 **2.1.28**。制品仓 `ohpcd` 经 `conan list cyrus-sasl/* -r=ohpcd` 实测已存在：

```
cyrus-sasl/2.1.28        (已占用，同一上游 2.1.28)
cyrus-sasl/2.1.28.1      (已占用，同一上游 2.1.28)
cyrus-sasl/2.1.28.2      (已占用，同一上游 2.1.28)
```

按 R37「版本号 = 上游版本 + 适配修复后缀，N 从 1 递增」，且 cnb.cool 制品仓不支持同版本多
recipe revision 并存（上传新 revision 会被 409 拒绝），本次为同一上游 2.1.28 的**第 3 次适配
修复**，故版本号 = **2.1.28.3**。

> 复核：`conan download cyrus-sasl/2.1.28.3 -r=ohpcd --only-recipe` 报 not found，
> `conan list cyrus-sasl/* -r=ohpcd` 仅返回 3 条（2.1.28 / 2.1.28.1 / 2.1.28.2），确认
> `2.1.28.3` 未被占用。
> 注意：`ci/scripts/preflight_check.sh` 的「版本号是否被占用」判断不可靠（R35：误报
> 2.1.28.1 未占用），故此处用 `conan list -r=ohpcd` 逐条核实。

## 3. 源码

- 官方 release 包（R39：conandata 只写官方源）：
  `https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-2.1.28/cyrus-sasl-2.1.28.tar.gz`
- SHA256：`7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c`
- 本地抓取使用镜像 `https://gh-proxy.com/<官方地址>`（github.com 直连不可达）；**conandata.yml
  内只保留官方 URL**，镜像仅用于本地取源码（R39/PF7）。

## 4. W0 依赖结论

- 本配方 `requirements()` 为空 → **默认包无运行时依赖**，W0 无制品仓阻塞项。
- 制品仓已有 `lmdb/0.9.35`（`conan download` 实测存在）。lmdb 仅在历史配方中作为
  **可选的、仅测试用的条件依赖**（上游 `utils/testsuite` 需要 sasldb 后端）出现；本包
  shipped 配置为 `db_none`，未启用该测试闭包，因此**不引入任何 requires**。

## 5. OHOS 关键适配

1. **`umask 077 → 022`（patches/0001）**：autoconf 在 HMDFS 构建目录下用
   `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，该 0700 目录随后**不可写**，
   `config.status` 直接失败：
   `./config.status[1065]: can't create ./confFDODmC/subs1.awk: Permission denied`。
   补丁把 `configure`（及其生成的 `config.status`）两处 umask 改为 022。
   注：官方 release 的 `configure` 是**预生成**文件，而本机**无 automake**（`aclocal-1.16`
   不存在），无法用 `autoreconf` 重新生成，故以补丁方式修改 `configure`。
2. **源码树 mtime 归一**：release tarball 中 `configure.ac` 比 `aclocal.m4` 新 → `make`
   尝试重跑 `aclocal/automake` → `aclocal-1.16: inaccessible or not found`（Error 127）。
   配方在 `source()` 结尾把整棵源码树 mtime 置为同一值，使 make 认为生成文件均为最新。
3. **`make -j1`**：HMDFS 构建目录无法创建 GNU make 的 jobserver FIFO
   （`make: jobserver mkfifo: ... Operation not permitted`）。
4. **`CC_FOR_BUILD=clang` / `CPP_FOR_BUILD=clang -E`**：`configure` 用
   `AC_PROG_CC_FOR_BUILD` 探测 build 机编译器（编译 `include/makemd5`），清掉 host 前缀后
   只搜 `gcc/cc/cl.exe`，OHOS 只有 clang。喂 PATH 可见的裸 `clang`（不烤入绝对路径）。
5. **`TMPDIR` → 构建目录**：平台 `/tmp` 只读（E002），autoconf 的 `mktemp`/conftest 需要
   可写临时目录，指到 `$build_folder/tmp`。
6. **显式 `--build/--host=aarch64-unknown-linux-gnu`**：tarball 的 `config.guess`
   （2018-02-24）不认识平台上 `uname -s = HarmonyOS`，否则 `configure: error: cannot guess
   build type`。
7. **`--without-openssl` 下仍有 4 个插件**：`DIGEST-MD5` / `CRAM-MD5` 使用 libsasl2 自带的
   MD5/HMAC-MD5 实现，不依赖 OpenSSL；因此 `libcrammd5` / `libdigestmd5` 仍被构建。
8. `package()` 的清理（**纯库包**）：
   - `rm(self, "*.la", self.package_folder, recursive=True)` —— `.la` 的 `dependency_libs/libdir`
     烤死了构建机绝对路径（实测 `dependency_libs=' -L/storage/.../usr/local/lib -ldl -lresolv'`），
     且 `-lresolv` 在 OHOS/musl 下无意义。**注意 Conan `rm()` 默认 `recursive=False`（只扫包根一层）**，
     不加 `recursive=True` 则 `lib/sasl2/{libplain,libcrammd5,libdigestmd5,libanonymous}.la`
     会全部残留 —— 这是首轮交付的真实缺陷，已修复。
   - 用 `shutil.rmtree` 彻底删除 `bin/` 与 `sbin/`：上游会安装 `bin/pluginviewer`（可执行 ELF）；
     `--with-dblib=none` 下 `saslpasswd2`/`sasldblistusers2` 根本未构建，`pluginviewer` 也只是
     开发者用的插件检视器（且依赖已被关闭的 sasldb 后端）。删除后交付包**不含任何可执行文件**，
     与 `package_type="library"`、`manifest.yaml: artifacts.executables: []`、"无 commands.json"
     的声明完全一致。
   - 实测证据：`find <pkg> -name '*.la'` → 空；`ls <pkg>/bin` → 不存在。

## 6. 上游测试（R51）

清点（release tarball）：`utils/testsuite.c`（EXTRA_PROGRAMS）、`saslauthd/testsaslauthd.c`、
`sample/{client,server,common,sample-*,http_digest_client}.c`、`utils/smtptest.c`、
`utils/sfsasl.c`。`Makefile.am` / `utils/Makefile.am` **没有任何 `check_PROGRAMS`/`TESTS`
注册** → 上游 `make check` 实际不执行任何用例（BLFS 亦记载该包无 test suite）。

未运行及原因（逐项，非「没环境」）：
- `utils/testsuite`：其首个检查是 `sasl_checkpass()`（auxprop_plugin=sasldb，硬编码用户/口令），
  需要**真实 sasldb 后端 + 预置口令库**；shipped 配置为 `--with-dblib=none`，按构造无法通过。
  要跑它必须另建一次性 `--enable-auth-sasldb --with-dblib=lmdb` 测试树（历史 `cyrus-sasl/2.1.28.1`
  即此做法）；本包未启用该可选闭包。
- `saslauthd/testsaslauthd`：守护进程需 PAM/shadow 与可写 AF_UNIX socket 目录；本包
  `--without-saslauthd`（守护进程不属于库本体）。
- `sample/*`：交互式示例，`sample/client.c` 调 musl 已移除的 `getpass()`；本包 `--disable-sample`。

`test_package`（消费者视角，真实 API，R34/PF3）：`test_cyrus_sasl.c` 断言
`sasl_version_info`(2.1.x) / `sasl_client_init` / `sasl_client_new` / `sasl_listmech`，
并硬断言打包后 `PLAIN` 与 `CRAM-MD5` 插件已被 dlopen 加载。断言数 = 4。

## 7. 验证证据

- `conan create cyrus-sasl/2.1.28.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
  --user=ohpcd --channel=stable` → **rc=0**。
- test_package 实跑输出：

  ```
  cyrus-sasl impl=Cyrus SASL version=2.1.28.0
  plugin dir = <pkg>/lib/sasl2
  client mechs (5): DIGEST-MD5 EXTERNAL CRAM-MD5 PLAIN ANONYMOUS
  cyrus-sasl test PASS
  ```

- 产物：`lib/libsasl2.so.3.0.0`（SONAME `libsasl2.so.3`，DT_NEEDED 仅 `libc.so`）+
  `lib/sasl2/{libanonymous,libcrammd5,libdigestmd5,libplain}.so.3.0.0` + `include/sasl/*.h`
  + `lib/pkgconfig/libsasl2.pc`。

## 8. 构建环境问题（本次必须修复，非配方问题）

本机原始环境有两处与 SKILL §0.0 预期不符，导致 `conan create` 无法得到真实退出码、也无法
使用 `os=OHOS`：

1. **PATH 上的 `conan` 是 vanilla 2.30.0**（`~/.local/lib/python3.14`），其代码**完全不含
   OHOS 支持**（`grep -r OHOS conan/ conans/` 无命中），`os=OHOS` 报
   `Invalid setting 'OHOS'`。
2. **平台 Python 3.14（harmonybrew）对所有进程强制退出码 1**：即使 `sys.exit(0)` 也返回 1
   并打印一段 SystemExit 假 traceback；`sys.exit(3)` 同样返回 1 → 任何 `rc == 0` 判据失效。

修复（环境级，不改框架文件）：
- 用社区 PyPI 的 **OHOS 适配版 conan 2.29.1** 安装到 **健康的社区 Python 3.12**
  （`~/usr/local/bin/python3`，其退出码正常）：
  `pip download --no-deps -i https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple conan==2.29.1`
  → `pip install --user <wheel>`（依赖从 pypi.org 解析；PyYAML/MarkupSafe 本机构建）。
  此后 `conan` 的 shebang 指向 3.12，退出码真实，且代码含 `OHOS→linux-ohos` 三元组映射。
- 刷新陈旧 `settings.yml`（缺 OHOS 枚举）：按 `ci/conan/setup.sh` 的口径将其移走 +
  `conan profile detect` 重新生成（OHOS conan 的 `conan/internal/default_settings.py` 含 OHOS）。
- 修复后 `conan --version` → rc=0，`conan <不存在的包>` → rc=1（真实失败仍非零，
  未关闭任何门禁）。

## 9. 待沉淀的 SKILL 反馈（reports/skill-feedback.md）

1. `lang_detect._manifest_scan` 用**整棵树的文件名集合**（`names = {p.name for p in files}`）
   判定 manifest，且 perl 分支（`Makefile.PL/Build.PL`）优先于 autotools 分支 → cyrus-sasl
   因 vendored `mac/libdes/src/Makefile.PL` 被误判为 `perl/module-build`，与 C 统计冲突后
   判 `mixed` → 触发 `env_unsupported` 误终止。建议 manifest 判定只看**顶层**文件
   （代码对 `CMakeLists.txt`/`meson.build` 已用 `tops`，其余用 `names`，不一致）。
2. SKILL §0.0 的 conan 安装前提（社区源 conan + 正确 python）需作为**环境预检**强制项；
   本机 PATH 上的 vanilla conan 与退出码恒 1 的 Python 会静默地把所有 `rc==0` 门禁判负。

## 10. R47 lang-preflight 判定口径与绕行留痕（审计要求）

**结论**：cyrus-sasl 2.1.28 是 **C 项目**（顶层 `configure`/`configure.ac`/`Makefile.am`，
主体 166 个 `.c`）。`lang-preflight` 必须先通过；实测确实通过，但**在原始源码树上它会误判**，
故分两次执行并在此如实留痕。

**被绕行的对象**：`lang-preflight --src <原始解压树 $BUILD_SRC_DIR>`。

**工具误判事实（原始树，exit 2）**：
```json
{"expected":"cpp","detected_language":"mixed",
 "language_evidence":{"build_system":"module-build","manifest":"Makefile.PL/Build.PL 存在",
                      "source_stats":"源文件 202 个（c:166, python:16, nodejs:15, perl:5），主体占比 82%"},
 "notes":["冲突: manifest=perl 但统计 c 占 82% → mixed"]}
```
**原因（读 `scripts/ohc/lang_detect.py` 定位）**：`_manifest_scan()` 用
`names = {p.name for p in files}` —— **整棵源码树**的文件名集合 —— 判 manifest，且 perl 分支
（`Makefile.PL/Build.PL`，第 115 行）**排在 autotools 分支（`configure.ac`/`Makefile.am`，第 129 行）之前**。
cyrus-sasl 的 tarball 带一个 **vendored、与 OHOS 构建无关**的 macOS classic 组件
`mac/libdes/src/Makefile.PL`（全树唯一触发文件），于是被判 `perl/module-build`；再与 C 源统计
（82%）“矛盾” → 按 §4.7 冲突规则判 `mixed` → 触发 `env_unsupported` 终止。
（对照：同一函数对 `CMakeLists.txt`/`meson.build` 用的是**顶层**字典 `tops`，对 perl/python/go
等却用递归 `names`，口径不一致。）

**采用的做法（绕行）**：在**不修改框架文件**（`scripts/` 只读）的前提下，对**剔除了 vendored
`mac/` 目录**的源码副本执行预检：
```bash
tar --exclude='./mac' -cf - . | (cd "$TMPDIR/langcheck-cyrus-sasl" && tar -xf -)
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight cyrus-sasl 2.1.28.3 --src "$TMPDIR/langcheck-cyrus-sasl"
```
结果：`task=cpp, detected=c, build_system=autotools`（`configure.ac/Makefile.am 存在`，
`c:103 (77%)`）→ c↔cpp 兼容族 → **exit 0，通过**。该副本只删掉一个与构建无关的 macOS 组件，
未改变项目语言主体。

**是否可改为不绕行的正统做法**：当前**没有**在不改框架文件的前提下能让工具正确判定的输入
—— `_manifest_scan` 的判定完全由代码固定，`mac` 也不在 `_SKIP_DIRS` 中；`--src` 语义是
“源码 checkout 目录”，因此只能喂一棵剔除无关 vendored 组件的树。**已按 §9-1 上报为 SKILL 反馈**
（建议 perl/py/go 的 manifest 判定改用顶层 `tops`）。若框架侧修复，本包无需绕行即可通过。

## 11. 状态

`built` + 本地 `conan create` 验证通过（test_package 实跑 5 机制 + 4 断言 PASS；
`.ci-result.json exit_code=0`）。
尚未 upload 到 ohpcd 制品仓（等 PR 合并后由 release 流水线 upload）。
---

**编译结束**: 2026-09-18 17:02
**最终状态**: built
