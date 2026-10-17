# cyrus-sasl-login 2.1.28 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，in-source 构建）
- 编译日期: 2026-09-11
- 编译器: clang/clang++（待 HMBS 真机预检确认版本）
- 状态: built（配方完成，待真机验证；验证通过前不标 published）
- 源码: https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-2.1.28/cyrus-sasl-2.1.28.tar.gz
- 源码 SHA256: 7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c（与 cyrus-sasl/2.1.28、2.1.28.1 同源同值）

## 定位

- 本包是 Cyrus SASL 的 LOGIN 机制包：同一份上游 2.1.28 源码，以 `--enable-login` 构建，
  产出静态 `libsasl2.a`（LOGIN/PLAIN/ANONYMOUS 等自包含机制经 `--with-staticsasl` 直接链入，
  无需运行期 `SASL_PATH`/dlopen 插件搜索）。
- 上游默认关闭 LOGIN（BLFS：unsupported LOGIN authentication method，需显式开启）；
  login.c 由 plain.c 派生，是纯明文交换机制，不依赖 openssl/lmdb/sqlite 等外部库，
  因此本包零 Conan 依赖，避免 krb5/openldap/sasl 循环依赖链。

## 编译步骤

标准 autotools 流程（conanfile.py `_build_ohos_tree` 等价逻辑）：

```bash
TMPDIR=<writable-tmp> CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh \
  CC_FOR_BUILD=clang CPP_FOR_BUILD="clang -E" \
  /system/bin/sh ./configure \
    --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
    --prefix=/ --disable-dependency-tracking \
    --disable-sample --disable-shared --enable-static --with-staticsasl \
    --disable-staticdlopen --disable-alwaystrue \
    --disable-gssapi --disable-httpform --disable-krb4 --disable-ldapdb \
    --disable-ntlm --disable-otp --disable-passdss --disable-sia \
    --disable-sql --disable-srp --disable-srp-setpass \
    --enable-login \
    --without-saslauthd --without-authdaemond --without-des --without-gdbm \
    --without-ldap --without-mysql --without-openssl --without-opie \
    --without-pam --without-pgsql --without-pwcheck \
    --without-sqlite --without-sqlite3 \
    --disable-auth-sasldb --with-dblib=none
make -j1
make install DESTDIR=<package> -j1
```

构建中另做两件 OHOS 适配（沿用 cyrus-sasl/2.1.28.1 已验证做法）：

- 把 `plugins/login.c`、`plugins/plain.c`、`plugins/anonymous.c`、`plugins/cram.c`、
  `plugins/digestmd5.c`、`sasldb/db_none.c` 拷贝到 `lib/`（静态链入）；
- `config/install-sh` 拷贝到可写 tmp，重写 shebang 为 `#!/system/bin/sh` 后
  经 make 变量 `MKDIR_P`/`INSTALL*` 以单一程序路径调用
  （libtool `--mode=install` 会把 `/system/bin/sh <script>` 前缀误解析为待安装文件，
  导致 `install-sh: no input file specified`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: no acceptable C compiler found`（预期） | configure 用 `AC_PROG_CC_FOR_BUILD` 清 host 前缀后裸搜 `gcc/cc/cl.exe`，OHOS 只有 clang（cyrus-sasl/2.1.28 已记录） | 显式喂 `CC_FOR_BUILD=clang` + `CPP_FOR_BUILD="clang -E"`（本机构建 build==host） |
| 2 | 老代码在 clang 15 下隐式声明升为 error（预期） | C99 隐式函数声明/整数转换在新 clang 默认为 error | `extra_cflags` 加 `-Wno-error=implicit-function-declaration -Wno-error=int-conversion`（发行版编老代码通用做法） |
| 3 | HMDFS 默认 tmp 不可写导致 conftest 失败（预期） | configure 落 conftest 到 TMPDIR | TMPDIR 优先取 HMBS 注入值，否则用源码树内 `tmp/` |
| 4 | 上游无自动化测试套件 | 顶层无 `make check`，utils 仅 EXTRA_PROGRAMS；BLFS 确认无 test suite | 按 no_tests 口径申报（MANIFEST.yml 完整审计），test_package 提供 6 项 LOGIN 消费者验证 |
| 5 | `make install` 在 `lib/install-libLTLIBRARIES` 报 `install-sh: no input file specified` | `INSTALL="/system/bin/sh <tmp>/install-sh -c"` 带 shell 前缀，libtool `--mode=install` 把脚本路径当成待安装文件解析 | install-sh 拷贝后重写首行为 `#!/system/bin/sh`（`copy2` 保留 tarball 可执行位，免 chmod），`INSTALL/MKDIR_P` 改为单一程序路径 `<tmp>/install-sh -c[-d]` |

## 源码修改

无。零补丁适配（LOGIN 机制自包含，仅依赖标准 C 库与 libsasl2 内部 `plugin_common`）。

## 依赖版本

无外部依赖（自包含；system_libs 仅 `pthread`）。

## 验证结果

本地 Windows 环境未执行编译与测试（按规范，真机验证由 HMBS 后台统一执行，
且除 rsync/ssh 方式外不允许在本机运行 conan）。

test_package 设计（test_login.c，6 项真实 API 验证，待真机实测）：

| # | 验证项 | 断言 |
|---|--------|------|
| 1 | 版本正确 | `sasl_version_info` 主/次版本 == 2.1 |
| 2 | 客户端初始化 | `sasl_client_init` 返回 SASL_OK |
| 3 | 建连 | `sasl_client_new("smtp", ...)` 成功 |
| 4 | 机制枚举 | `sasl_listmech` 返回 SASL_OK |
| 5 | LOGIN 可用 | 枚举串含 `LOGIN`（本包核心目的） |
| 6 | PLAIN 可用 | 枚举串含 `PLAIN`（静态机制表链入证明） |

构建期另有 `pluginviewer -c` 烟雾检查（上游自带工具列出客户端机制，
证明 LOGIN 插件对象已编译链接；交叉构建时跳过）。

## 交付物

待真机预检产生（lib/libsasl2.a + include/sasl/*.h + lib/pkgconfig/libsasl2.pc）。

## 注意事项

- 本包与 `cyrus-sasl` 同源但包名/用途不同：`cyrus-sasl` 覆盖完整机制集（含 openssl/lmdb/sqlite3 依赖），
  本包是 LOGIN 专用最小闭包（零依赖、静态、无守护进程），供只需要 LOGIN 的消费方选用。
- 静态库 + `--with-staticsasl`：消费方无需设置 `SASL_PATH`，LOGIN 无运行期插件加载。
- LOGIN 是明文机制（BLFS 标注 unsupported/insecure by nature），仅用于兼容需要它的老协议场景。
- 本轮未提交、未推送，待 HMBS 真机全部门禁通过后统一提交。
