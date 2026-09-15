# cyrus-sasl-gssapiv2 2.1.28 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，in-source 构建）
- 编译日期: 2026-09-12
- 编译器: clang/clang++（待 HMBS 真机预检确认版本）
- 状态: built（配方完成，待真机验证；验证通过前不标 published）
- 源码: https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-2.1.28/cyrus-sasl-2.1.28.tar.gz
- 源码 SHA256: 7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c（与 cyrus-sasl/2.1.28、2.1.28.1 同源同值，已在本机对下载包实测一致）

## 定位

- 本包是 Cyrus SASL 的 GSSAPI 机制包：同一份上游 2.1.28 源码，以
  `--enable-gssapi=<krb5包目录> --with-gss_impl=mit` 构建，默认产出静态
  `libsasl2.a`（GSSAPI 经 `--enable-static/--disable-shared` 真静态直接链入，消费方无需运行期
  `SASL_PATH`/dlopen 插件搜索）；`shared=True` 时产出 `libsasl2.so` +
  `lib/sasl2/libgssapiv2.so` 动态插件。
- 上游自己也把 GSSAPI 视作独立包：`win32/conan/gssapiv2/conanfile.py` 包名即
  `cyrus-sasl-gssapiv2`，且 requires Kerberos GSSAPI 实现——本包把这份依赖
  落到 `krb5/1.22.1`（MIT 实现）。
- `cyrus-sasl/2.1.28` 主包显式 `--disable-gssapi`（当时 krb5 未进制品仓，避
  循环依赖）；本包是 GSSAPI 专用闭包，与主包互补而非重复。

## 依赖（ohpcd 制品仓）

- `krb5/1.22.1`：MIT Kerberos GSSAPI 提供方（头文件 `gssapi/gssapi.h` +
  `-lgssapi_krb5 -lkrb5 -lk5crypto -lcom_err`）。已发布证据：合入 main 的
  `canl-c/3.0.0`（`deps["krb5"].cpp_info.includedirs` 头文件用途）与
  `python-gssapi/1.8.3`（链接上述 4 个库）均从制品仓解析该版本，PF4/L0i 合规。
- 无 openssl/lmdb/sqlite3 依赖：GSSAPI 密码学由 krb5 提供，
  `--without-openssl --with-dblib=none` 保持闭包最小。

## 关键适配（上游源码实测得出的 delta）

1. **`--enable-gssapi=<krb5包目录>`**：`m4/sasl2.m4` 的 `SASL_GSSAPI_CHK`
   在参数为目录时自动追加 `-I<DIR>/include` / `-L<DIR>/lib` 到探测，
   无需 AutotoolsDeps 注入（避开 krb5 长 libs 列表污染 configure 链接测试）。
2. **`--with-gss_impl=mit`**：跳过 heimdal/cybersafe/seam 探测，直取 MIT
   链接行 `-lgssapi_krb5 -lkrb5 -lk5crypto -lcom_err`（与 krb5/1.22.1 产物一致）。
3. **防静默丢失机制**：探测失败时上游只告警（`gssapi="no"`）不断构建——这对
   本包是致命静默。配方做双保险：generate 期校验 krb5 包布局
   （`include/gssapi/gssapi.h` + `lib/` 存在）；configure 后断言 `config.h`
   含 `HAVE_GSSAPI`，缺失即抛错。
4. **静态符号闭包已审计**：`gssapiv2_client/server_plug_init` 就在
   `plugins/gssapi.c` 尾部（与 login.c 自带 LOGIN 入口同模式），故静态只需
   拷贝 `plugins/gssapi.c` + `sasldb/db_none.c` 到 `lib/`；上游不存在
   `STATIC_GS2` 接线（全树实测仅 `STATIC_GSSAPIV2` 在 `lib/staticopen.h`，本轮追加断言静态必含该宏），
   即使 gs2 自动启用（SASL_GSSAPI_CHK 在 krb5 头提供 RFC5587/5801 时自动加 `gs2.c`），拷贝逻辑改为解析 `lib/Makefile` 的 `SASL_STATIC_SRCS` 全量拷贝，不再硬编码子集。
   真静态（`--disable-shared --enable-static --without-staticsasl`）下
   `utils/*`（dbconverter-2、pluginviewer）直链 `../lib/.libs/libsasl2.a`，
   故 configure 参数额外喂 `LIBS=-L<krb5>/lib -lgssapi_krb5 -lkrb5 -lk5crypto -lcom_err`
  （与 `--with-gss_impl=mit` 同一 MIT 链接行；只动 LIBS，不碰 LDFLAGS，避免覆盖工具链 sysroot），
   否则全量 `gss_*` 未定义符号导致 `ld.lld` 在 `utils` 链接期失败。
5. **`CC_FOR_BUILD=clang`**：`AC_PROG_CC_FOR_BUILD` 裸搜 `gcc/cc/cl.exe`，
   OHOS 只有 clang（cyrus-sasl/2.1.28 已记录），本机构建 build==host，显式喂入。
6. **老代码降 warning**：`-Wno-error=implicit-function-declaration
   -Wno-error=int-conversion`（clang15 默认升 error，发行版编老代码通用做法）。
7. **TMPDIR → HMBS 注入值或源码树内 `tmp/`**：HMDFS 默认 tmp 可能不可写。
8. **umask 077→022 + mktemp fallback shim + install-sh shebang 重写**：
   沿用 cyrus-sasl-login/2.1.28 已合入评审的做法（E011/HMDFS、
   libtool `--mode=install` 单程序路径要求）。
9. **shared=False 时清掉残留 .so/.la**：防消费方 DT_NEEDED 误链系统残桩
   （login 同款）；shared=True 时只清 `.la`（构建机绝对路径），保留插件 `.so`。

## 构建期烟雾检查

- `utils/pluginviewer -c`（上游自带机制列表工具）输出必须含 `GSSAPI`
  （只看退出码等于没测，输出断言才是证明；需 KDC 的真实认证不在构建期做）。
- 静态：`SASL_PATH` 指向空目录——列出的 GSSAPI 只能来自静态机制表；
  动态：`SASL_PATH` 指向构建树 `plugins/.libs` 且 `libgssapiv2.so` 必须存在。

## 上游测试审计

- 与 cyrus-sasl-login 同源同结论：顶层 `Makefile.am` 无 check 目标；
  `utils/Makefile.am` 仅 `EXTRA_PROGRAMS`（testsuite/testsuitestatic/smtptest），
  无 `TESTS`/`check_PROGRAMS`；无 gtest/ctest/pytest/meson wiring；
  BLFS 明确记录无测试套件 → `no_tests` 口径（MANIFEST.yml 完整审计）。
- GSSAPI 补充：即使手动跑 `utils/testsuite`，它也不覆盖 GSSAPI
 （GSSAPI 认证需要可用 KDC），故无“可低成本补齐的上游用例”。

## 验证结果

本地 Windows 环境未执行编译与测试（按规范，真机验证由 HMBS 后台统一执行，
且除 rsync/ssh 方式外不允许在本机运行 conan）。

test_package 设计（test_gssapiv2.c，6 项真实 API 验证，待真机实测）：

| # | 验证项 | 断言 |
|---|--------|------|
| 1 | 版本正确 | `sasl_version_info` 主/次版本 == 2.1 |
| 2 | 客户端初始化 | `sasl_client_init` 返回 SASL_OK |
| 3 | 建连 | `sasl_client_new("smtp", ...)` 成功 |
| 4 | 机制枚举 | `sasl_listmech` 返回 SASL_OK |
| 5 | GSSAPI 可用（客户端） | 枚举串含 `GSSAPI`（本包核心目的） |
| 6 | GSSAPI 可用（服务端） | `sasl_server_new` + `sasl_listmech` 枚举串含 `GSSAPI` |

机制枚举无需 KDC/凭证；`LD_LIBRARY_PATH`（krb5 共享库）与共享构建下的
`SASL_PATH` 由 test 包显式注入子进程环境，不依赖外部配置。

## 交付物

待真机预检产生（默认静态：lib/libsasl2.a + include/sasl/*.h +
lib/pkgconfig/libsasl2.pc；shared=True 时另有 libsasl2.so +
lib/sasl2/libgssapiv2.so）。

## 注意事项

- 本包与 `cyrus-sasl` 同源但用途不同：主包覆盖完整机制集（含
  openssl/lmdb/sqlite3 依赖、禁 GSSAPI），本包是 GSSAPI 专用最小闭包
  （仅依赖 krb5），供需要 Kerberos 认证的消费方选用。
- GSSAPI 真实认证需要可用 KDC，本包只保证机制可用性（枚举 + 插件加载），
  不在测试中做 `gss_init_sec_context` 握手。
- 本轮未提交、未推送，待 HMBS 真机全部门禁通过后统一提交。

## 2026-09-12 真机轮修复（pluginviewer rc=0 但 GSSAPI 未列出）
- 现象：`_run_gssapi_smoke_test` 抛 `GSSAPI smoke test failed: rc=0, GSSAPI listed=False`；构建日志显示 `libanonymous.so` 等共享插件仍在构建且 `pluginviewer` 链接 `../lib/.libs/libsasl2.so`。
- 根因：静态分支同时传 `--disable-shared` 与裸 `--with-staticsasl`，而上游 `configure.ac` 遇到 `with_staticsasl=yes` 即强制 `enable_shared=yes`，导致实际编出双库；`pluginviewer` 链接共享库（`DO_DLOPEN`+`PIC`，静态表被跳过），而烟雾检查却用空 `SASL_PATH` 期望静态表，只能失败。
- 修复：静态分支改用 `--without-staticsasl`（保持 `--disable-shared` 有效，实现真静态单库）；显式 `--disable-anon/--disable-plain` 收敛为 GSSAPI 专用闭包（与文档一致）；`_copy_linksrcs_for_ohos` 改为解析 `lib/Makefile` 中 `SASL_STATIC_SRCS` 全量拷贝（含自动启用的 `gs2.c`）；`config.h` 断言追加 `STATIC_GSSAPIV2`；烟雾检查前记录 `config.h`（`HAVE_GSSAPI/STATIC_GSSAPIV2/DO_DLOPEN`）、`lib/Makefile` 静态变量与 `lib/.libs` 产物供下轮研判。

## 2026-09-12 真机轮修复（configure 报 cannot run C compiled programs + [readonly_tmp]）
- 现象：`checking for C compiler default output file name... a.out` 后 `configure: error: cannot run C compiled programs`；同期预检脚本报 `can't create temporary file /tmp/sh*.tmp: Read-only file system`，HMBS 平台诊断为 `[readonly_tmp]`。
- 根因（待下轮真机验证）：配方用裸 `self.run(command)` 直调 configure/make，未传 `env="conanbuild"`，`AutotoolsToolchain` 生成的工具链环境（OHOS CC/sysroot）对子进程不可见，configure 的 conftest 链接/执行退化到环境默认编译器；同时可写 TMPDIR 只靠行内前缀传递，未进入 conanbuild 聚合环境，clang 中间文件仍可能触碰只读 `/tmp`。
- 修复：`build()`/`package()` 的三处 `self.run` 补 `env="conanbuild"`；`generate()` 经 `Environment` 把 `TMPDIR/TMP/TEMP`、`CONFIG_SHELL/SHELL`、`CC_FOR_BUILD/CPP_FOR_BUILD` 存入 conanbuild 聚合脚本（行内前缀保留，双保险）；`_writable_tmpdir` 改为真实创建探针文件验证可写；`_build_cc_for_ohos` 按 profile conf → `$CC`/`$CC_FOR_BUILD` → PATH 绝对路径逐级回退，避免命中宿主工具链；新增 `_device_shell_for_ohos` 统一设备 shell 选择。

## 2026-09-12 真机轮修复 configure cannot run C compiled programs 加源码下载超时
- 现象：source() 两次 ConnectTimeout 后重试成功；随后 configure 在
  checking whether we are cross compiling 处报 cannot run C compiled programs。
- 根因：配方把 MIT 链接行以全局 LIBS=xxx configure 参数传入。LIBS 是 precious
  变量，autoconf 把它追加到每一个链接测试（含首个 AC_PROG_CC 自检），而
  krb5/1.22.1 默认 shared=True（共享 .so），conftest 链接后执行时加载器找不到
  libgssapi_krb5.so 等（无 AutotoolsDeps、无 LD_LIBRARY_PATH），遂报 cannot run。
- 修复：configure 参数不再传全局 LIBS；新增 _gssapi_libs()，经 _ohos_make_vars()
  以 make 期 LIBS= 变量覆盖传入（自动传播到各子 make，不污染 configure）；
  configure/make 行内与 generate() conanbuild 聚合环境同步前置
  LD_LIBRARY_PATH=<krb5>/lib；conandata.yml 的 url 改为有序列表（gh-proxy 镜像
  在前、官方 URL 保底，sha256 不变，复用 build_and_test.sh 的 GitHub 镜像映射）。
