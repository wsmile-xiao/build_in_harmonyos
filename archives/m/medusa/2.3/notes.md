# medusa 2.3 适配笔记

任务：A 类，任务 ID 8771，分支 `feat/medusa-2.3`，归档 `archives/m/medusa/2.3/`。

## 1. 结论速览

| 项目 | 状态 |
| --- | --- |
| W0 依赖检查 | 4 个依赖全部已发布（openssl/3.0.21、libssh2/1.11.1、libgcrypt/1.11.0、libsmb2/6.2） |
| 源码 URL + sha256 | 官方 release 资产，sha256 已核对 |
| 构建系统 | GNU Autotools（release tarball 自带 configure/Makefile.in/aclocal.m4） |
| 配方 | `conanfile.py` + `conandata.yml` + 7 个补丁 + 软件级 `commands.json` |
| test_package | 两层：`test_medusa.sh` 执行包内 `medusa -d`（剔除 `Couldn't load` / `Invalid module` 失败行后统计，22 个模块 dlopen 成功）；`test_medusa_e2e.sh` 完整消费者用例（对本机 FTP 服务发起真实审计并命中口令 + 错误口令反向对照），共 17 条断言 |
| **真机 conan create** | **成功**（`Success: 1 / Failed: 0`，L0/L1/L5 = pass，L2 = skip，L4 = warn） |
| 真机运行 | 包内 `bin/medusa -V` 成功；`-d` 列出 22 个服务模块 |
| **知识提炼（路径 B）** | 2 条草稿 + 证据报告，见 §10 |

真机验证环境：`feat/medusa-2.3` 归档最小集 → 隔离 job `$HOME/ohos-users/medusa/medusa-2.3-build`
（独立 `CONAN_HOME`、独立 `RUN_DIR`），profile `ohos-aarch64-localdevice`，
runner `$HOME/bin/ohos-test-runner.sh --mode heavy --try-lock`。

## 2. 上游构建系统分析

- `configure.ac`（AC_INIT medusa 2.3）→ 生成 272 KB 的 `configure`（GNU Autoconf 2.72）。
- `Makefile.am`：`SUBDIRS = src`；`src/Makefile.am`：`SUBDIRDS = modsrc`、`bin_PROGRAMS = medusa`。
- `src/modsrc/Makefile.am`：`modulesdir = $(libdir)/medusa/modules`，每个协议一个 `*.mod`
  （共享对象），条件编译由 configure 的平台探测决定。

关键结论：

1. **没有测试套件**：`Makefile.am` 无 `TESTS`/`check_PROGRAMS`，tarball 无 test 目录，
   `make check` 只是 automake 空目标；因此本库自带两层验证：`test_medusa.sh` 校验产物
   （二进制启动 + 22 个模块 dlopen），`test_medusa_e2e.sh` 是完整消费者用例——在 loopback
   上拉起带唯一合法口令的 FTP 服务（`ftp_e2e_server.py`，仅用 python3 标准库），再用包内
   二进制发起真实审计，必须命中口令并输出 `ACCOUNT FOUND … [SUCCESS]`，且错误口令不得误报。
2. **平台判定只认 `$target`**：`case "$target" in *linux*)` 命中 `aarch64-unknown-linux-ohos`，
   所以难点在三元组识别与 `-lrt`，而不在分支缺失。
3. **OpenSSL 必需且启动即用**：`configure` 缺 OpenSSL 直接报错；核心程序在解析命令行
   **之前**就无条件 `OSSL_PROVIDER_load(NULL, "default")` 与 `("legacy")`，任一为 NULL 即
   `ERR_FATAL` 退出。
4. **模块是运行期插件**：`DEFAULT_MOD_PATH` 是编译期绝对路径，Conan 包内不可能命中；
   上游支持 `MEDUSA_MODULE_PATH` 覆盖，配方在 `package_info()` 里导出该变量。

## 3. 补丁说明（7 个，单一职责）

| 补丁 | 目标 | 真机验证到的现象 |
| --- | --- | --- |
| 0001-config.guess.patch | 识别 `uname -s = HarmonyOS` → `aarch64-unknown-linux-ohos` | 修复前 `configure: error: cannot guess build type` |
| 0002-config.sub.patch | 接受并规范化 `linux-ohos` 三元组 | 修复前 config.sub 输出 `…-linux-gnu-ohos`；`-linux*)` 规则会把 os 改写成 `linux-gnu` |
| 0003-configure-ohos-link-flags.patch | OHOS 下从 `LIBDL` 去掉 `-lrt` | 全系统无 librt（详见 §4） |
| 0004-configure-config-status-tmpdir.patch | `config.status` 工作目录不再用 `umask 077` 创建 | 修复前 `./confXXXXXX/subs1.awk: Permission denied` |
| 0005-thread-pool-no-cancel-capability.patch | 取消类调用按 `HAVE_PTHREAD_CANCEL` 条件编译；无该能力时走 `POOL_DESTROY` + `pthread_cond_broadcast` 协作关闭 | 修复前链接失败：`undefined symbol: pthread_cancel / pthread_setcancelstate / pthread_setcanceltype` |
| 0007-pthread-cancel-capability-guard.patch | `configure` 探测 `pthread_cancel` 并定义 `HAVE_PTHREAD_CANCEL`（`configure.ac` / `configure` / `config.h.in` 同步） | 为 0005 提供能力宏；**避免在 `patches/` 中引入 `__OHOS__` 平台宏（R8）** |
| 0006-ohos-ssh-module-gcrypt-wrapper.patch | OHOS 跳过 libssh2 的 libgcrypt 兜底探测 | 修复前 `SSH ** Disabled **`（见 §5） |

关于 0001：仓库标准脚本 `scripts/patch-autotools-ohos.pl` 插入的分支只有 `GUESS=...`
而**没有** `echo "$GUESS"; exit`，config.guess 的每个分支都必须负责输出，否则脚本会继续
往下走到 "unable to guess system type"。本补丁在脚本输出基础上补齐了 `echo`/`exit`。
这一点值得回写知识库（E007 的建议方案在该脚本上不完整）。

关于 0002：上游 `config.sub` 是 2018-02-22 版（无 `field1/field2` 重构），标准脚本的 3 处
替换全部落空，需要手工补 2 处（`maybe_os` 白名单 + `-linux-ohos*)` 分支）。
`config.guess` 与 `config.sub` 均用 stub `uname` 做过行为验证：

```text
config.guess (HarmonyOS)         → aarch64-unknown-linux-ohos
config.guess (Linux, 回归)        → aarch64-unknown-linux-gnu
config.sub aarch64-linux-ohos    → aarch64-unknown-linux-ohos
config.sub x86_64-pc-linux-gnu   → x86_64-pc-linux-gnu
```

## 4. 依赖与开关策略

| 依赖 | 版本 | 作用 |
| --- | --- | --- |
| openssl | 3.0.21 | 必需；TLS/摘要/加密，并提供 `legacy` provider |
| libssh2 | 1.11.1 | SSH 模块 |
| libgcrypt | 1.11.0 | libssh2 线程安全路径（OHOS 上 `ldd` 不可用，见 §5） |
| libsmb2 | 6.2 | SMBNT 的 SMBv2/3 支持（`with_smb2`，默认关） |

**为什么是 openssl/3.0.21 而不是 3.5.6.x**：medusa 启动无条件加载 `legacy` provider；
3.5.6.x 的配方传 `no-legacy no-module` 并删除 `lib/ossl-modules`，加载必然失败。
3.0.21 配方未禁用，包内确实带 `lib/ossl-modules/legacy.so`（3.2 MB，真机实测可加载）。
真机实测：设置 `OPENSSL_MODULES` 后 `OSSL_PROVIDER_load(NULL,"legacy")` = OK、
`EVP_MD_fetch("MD4")` = OK。

**版本冲突与 override**：`libssh2/1.11.1` 固定依赖 `openssl/3.5.6.1`，直接 `self.requires`
会报 `Version conflict: Conflict between openssl/3.5.6.1 and openssl/3.0.21`，因此用
`self.requires("openssl/3.0.21", override=True)` 统一到 3.0.21；libssh2 用同一套
`OPENSSL_*` 变量重新构建成功（真机验证）。

**provider 打进本包**：`package()` 把 openssl 包的 `lib/ossl-modules/*.so` 复制到
`<pkg>/lib/ossl-modules`，`package_info()` 用它定义 `OPENSSL_MODULES`。
原因见 §6「package_folder 在 generate() 中不可用」。

显式关闭的模块（对应库均未在制品仓发布，configure 本就 warn 后自动禁用）：
`--enable-module-afp=no`、`--enable-module-ncp=no`、`--enable-module-postgres=no`、
`--enable-module-rdp=no`、`--enable-module-svn=no`、`--enable-module-smbnt-smb2=no`。

## 5. libssh2/libgcrypt 探测链（补丁 0006 的由来）

medusa 的 SSH 模块判定链：

1. `AC_CHECK_LIB(ssh2, main)` → **yes**；
2. 用 `ld --verbose | grep SEARCH_DIR` 找 `libssh2.so` → 找不到（`ld` 不是 GNU ld）；
3. 用 `ldd`/`otool` 判断 libssh2 的加密后端 → OHOS 上两者都没有 →
   `check_libgcrypt="true"`（"Assuming it was..."）；
4. `AC_CHECK_LIB(gcrypt, gcry_control)` → **yes**；
5. 但第 3 步为真时还要求 `AC_CHECK_LIB(gnutls, gnutls_handshake)` → **no** →
   `check_module_ssh="false"` → **SSH 模块被静默禁用**。

制品仓的 libssh2 实际是 OpenSSL 后端，而 OHOS 没有 gnutls，所以第 3 步的兜底假设在此不成立。
补丁 0006 在 `$target` 形如 `*ohos*` 时直接 `check_libgcrypt="false"`，跳过 ldd/otool 探测。
真机验证：`checking whether to enable SSH module... yes`、构建摘要 `SSH Enabled`、
`ssh.mod` 生成且能被 `medusa -d` 加载（22 个模块）。

## 6. OHOS 平台坑（本轮实际踩到并解决）

| 现象 | 根因 | 处理 |
| --- | --- | --- |
| `cannot guess build type` | config.guess 2018 版不认 HarmonyOS；标准脚本插入的分支缺 `echo`/`exit` | 补丁 0001 |
| `Invalid configuration 'aarch64-linux-ohos'` | config.sub 2018 版无 ohos；且 `-linux*)` 会把 os 改写成 `linux-gnu` | 补丁 0002 |
| `checking None/include/openssl/ssl.h... not found` | `self.dependencies["openssl"].package_folder` 在 `generate()` 阶段为 `None`，`--with-ssl=None` | 用 `cpp_info.location`、再从 Conan store 兜底定位包目录 |
| `AutotoolsToolchain` 无 `extra_cppflags` | Conan 2.29.1 只提供 `extra_cflags/extra_cxxflags/extra_ldflags`；且 medusa 的 configure 会重置 CPPFLAGS | include 走 CFLAGS/CXXFLAGS |
| `cannot run C compiled programs` | `AutotoolsToolchain` 导出的依赖 `LIBS`（`-lgcrypt -lgpg-error -lssh2`）被 configure 追加到每个 conftest，运行时找不到 `.so` | 给依赖 `-L` 目录补 `-Wl,-rpath` |
| `./confXXXXXX/subs1.awk: Permission denied` | OHOS `/storage/Users` 为 `hmmac=use_task`，`umask 077` 建出的 `drwx--S---` 目录**连属主都不能写入** | 补丁 0004（且 runner 已设 `TMPDIR`，否则先撞 `/tmp` 只读） |
| `undefined symbol: pthread_cancel` 等 | libc 未实现线程取消类 API（OHOS musl 即如此） | 补丁 0005 + 0007（能力探测，非平台宏） |
| `make: jobserver mkfifo … Operation not permitted` | OHOS 不允许建 FIFO（避坑指南 §15） | `autotools.make(args=["-j1"])` |
| `aclocal-1.17: command not found` | 补丁改了 `configure.ac`，时间戳使 make 想重跑 automake | 补丁后重新 touch 生成物时间戳 |
| 真机无法访问 github.com | 真机网络策略（避坑指南 §八-18） | 按 sha256 名把官方 tarball 注入 `$HOME/conan_dl_cache/s/`（CI 侧自带镜像 fallback） |
| `copy(..., delete=True)` | Conan 2 的 `copy()` 无此参数 | 改用 `rm()` |

## 7. 真机验证记录

```sh
# 入口
. "$HOME/ohos-users/medusa/medusa-2.3-build/env.sh"
cd "$CI_REPO_ROOT"
sh "$HOME/bin/ohos-test-runner.sh" --user medusa --lib medusa \
  --task medusa-2.3-final --mode heavy --try-lock --workdir "$CI_REPO_ROOT" \
  -- zsh ci/conan/build_and_test.sh "$CI_PACKAGES"
```

结果（最终 RUN_DIR `$HOME/ohos-test-runs/medusa-medusa-medusa-2.3-final-20260929-170943-34668`）：

```text
configure: checking build  system type... aarch64-unknown-linux-ohos
configure: checking host   system type... aarch64-unknown-linux-ohos
configure: checking target system type... aarch64-unknown-linux-ohos
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
  Success: 1
  Failed:  0
```

产物：`bin/medusa`（883 KB，含 `.codesign` 段）、`lib/medusa/modules/*.mod`（22 个）、
`lib/ossl-modules/legacy.so`、`share/man/man1/medusa.1`。

包内二进制自包含运行验证：

```text
$ OPENSSL_MODULES=<pkg>/lib/ossl-modules MEDUSA_MODULE_PATH=<pkg>/lib/medusa/modules <pkg>/bin/medusa -V
（成功，rc=0）
$ ... <pkg>/bin/medusa -d | <统计>
22
```

### L2 / L4 说明（非缺陷）

- **L2 = skip**：CI 的烟测用 `bin --version` / `bin --help`。medusa 的 `-V` 是版本，
  `-h` 是 **host 参数**（不是 help），没有 `--version`/`--help` 选项，所以该通用探测必然
  失败并 skip。实际可用性由 test_package 的 `medusa -d`（22 个模块）覆盖。
- **L4 = warn**：「dangerous functions found in patches」来自补丁文本中出现
  `pthread_cancel`（0005 的 `#ifdef HAVE_PTHREAD_CANCEL` 分支）与 `mktemp`（0004），均为平台适配所需且
  非新增调用；OHOS 分支并不调用 `pthread_cancel`。

## 8. 下一步命令

```sh
# 单包 shadow CI（排队，勿扫全仓）
/path/to/run-ohos-shadow-ci.sh archives/m/medusa/2.3

# 或等价真机命令（见 §7）
```

交付前确认：`Build Summary` 的 `Total: 1`；L0 全通过（含 L0k `commands.json`、L0m 目录结构、
L0n 分支名 `feat/medusa-2.3`）；L2 按上文说明为 skip；L5 `bin/` 有内容。

## 9. 已知限制（需在 PR 说明中保留）

- SMBv2/3（libsmb2）默认关闭（`with_smb2=False`）：上游要求 `<prefix>/include/smb2/smb2.h`，
  而制品仓 libsmb2 的公开 include 布局需单独确认后再打开；原生 SMBv1 SMBNT 模块已启用。
- RDP/AFP/NCP/PostgreSQL/SVN 模块在 OHOS 上没有可用依赖，属功能裁剪（均为上游可选模块）。
- openssl/3.0.21 在制品仓只有 `shared=False`；`libssh2.so` 内嵌 3.5.6.1 静态副本的隐患
  经 override 统一到 3.0.21 后已消除（真机 `ssh.mod` 正常加载）。
- `legacy.so`（3.2 MB）随包分发，使包体积从 ~2 MB 增至 ~5.4 MB，换来"开箱即用"。

## 10. 知识提炼（路径 B：知识库扩展）

本轮沉淀 2 条草稿，均满足"解决一类问题，非单库补丁"的判据，证据见
`reports/knowledge-evidence.md`：

| 草稿 | 主题 | 判据 |
| --- | --- | --- |
| `knowledge/drafts/DRAFT-medusa-conan-generate-dep-paths.{kv,md}` | Conan 2 `generate()` 中依赖包目录不可用；Autotools 标志必须从已物化数据推导（含 `extra_cppflags` 不存在、conftest 继承 LIBS 导致假阳性） | **全库无覆盖**；本仓库 1304 个配方在 `generate()` 中读取 `package_folder`，属 API 边界问题 |
| `knowledge/drafts/DRAFT-medusa-autotools-platform-triplet-and-probe.{kv,md}` | autotools OHOS 平台判定三处缺口：标准脚本插入的 config.guess 分支缺 `echo/exit`、config.sub 归一化顺序、假设式降级探测静默禁用功能 | E007/E072 未覆盖"脚本插桩不输出""`-linux*)` 改写顺序""静默禁用"三点，属增量；第 3 点还给出"构建全绿≠功能完整"的运行期断言兜底 |

已有条目覆盖、**未重复申报**的部分：`umask 077` + `config.status`（E011/E060/E112）、
pthread 取消类接口缺失（E085/E127）、FIFO 限制（E074/P020）。
