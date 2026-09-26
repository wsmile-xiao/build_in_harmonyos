# gss-ntlmssp 1.2.0 适配笔记

## 编译环境
- 构建系统: autotools（上游 tag 归档不含 configure → build() 内 autoreconf -f -i 自举）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 / clang++（profile ci/conan/profiles/ohos-aarch64：os=OHOS os.version=6.0 arch=armv8 libc++ Release）
- 状态: built

## 编译步骤

1. **依赖**：`krb5/1.22.1`（GSSAPI 硬依赖）、`libunistring/1.0`、`openssl/3.0.21`、`zlib/1.3.1`——
   四件全部先用真实 `conan install --build=never -pr <ohos-aarch64>` 验证二进制可取（W0-2）。
   tool_requires：`autoconf/2.72 + automake/1.18 + libtool/2.5.4`（tag 归档无 configure，CI worker 无 automake/libtool）。
2. **autoreconf -f -i**（显式 `ACLOCAL=/AUTOMAKE=<_perlshim>` + tools-first PATH，见问题 1/2）。
3. **configure**：`--without-wbclient --disable-nls --without-manpages`
   `--build/--host=aarch64-unknown-linux-gnu`（uname -s=HarmonyOS，config.guess 不识别，见问题 5）
   `--with-openssl=<conan openssl 包目录>`（AX_CHECK_OPENSSL 见问题 6）
   + conanautotoolsdeps 注入的 CPPFLAGS/LDFLAGS（krb5/unistring/openssl/zlib 的 -I/-L）。
4. **make -j2** 与 **make -j2 check**：均带命令行 `LIBS="-pthread -lunistring -lssl -lcrypto -lgssapi_krb5 -lkrb5 -lk5crypto -lcom_err -lz"`
   （见问题 7；值必须整体加引号，conan 拼参不转义）。
5. **package**：`make install`（DESTDIR=package_folder，prefix=/）→ 清理 .la → 核产物实物
   （lib/gssntlmssp/gssntlmssp.so + include/gssapi/gssapi_ntlmssp.h，缺失即抛错防 install 假绿）。
6. **test_package**：dlopen 安装树模块并做端到端 NTLM 会话（凭据→四步握手→wrap/unwrap→mic→释放），
   20 条断言；注入 `OPENSSL_MODULES`（见问题 4）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf` 崩 `Perl_my_cxt_init: symbol not found`（rc=255） | conanbuildenv 的 PATH 把 `/data/service/hnp/bin` 排在 tool_requires 之前 → 命中 HNP perl 5.42.0（非 i-thread），而 PERL5LIB 指向 conan perl 5.42.2（thread-multi）的 XS，两者 ABI 互不兼容（device-facts §一.23 的另一半） | build() 内把 tool_requires 各包 `bin/` **前置**到 PATH，且 autoreconf 用**命令行内联 PATH 前缀**（os.environ 改写会被 conanbuild 环境脚本重排覆盖，实测） |
| 2 | 即便 PATH 正确，`aclocal` 仍崩（.aclocal-real line 31） | ohpcd `automake/1.18` 的 `.aclocal-real/.automake-real` shebang 写死 `#!/data/service/hnp/bin/perl`（与 PERL5LIB 的 conan perl 互斥，方向不可调和）；且 `autoreconf` 经 `$ACLOCAL/$AUTOMAKE` **绝对路径**调用会绕过 PATH shim | ①生成 `_perlshim/{aclocal,automake}` 显式 `exec <conan perl> <.real>`；②shim 必须复刻 conan 包装的重定位参数（`--automake-acdir/--system-acdir/--libdir`，其 .real 编译进的前缀是 `//share/...`）；③内联 `ACLOCAL=/AUTOMAKE=` 钉到 shim |
| 3 | 编译错：`secure_getenv` 未声明/未定义（-Werror-implicit-function-declaration） | OHOS/musl libc **既无头文件声明也无链接符号**（probe 实测：stdlib.h 无声明；带 extern 声明链接 undefined symbol） | 补丁 0001：非 glibc/bionic 平台用等价判据内联实现（uid/gid 真实==effective 才读环境） |
| 4 | 上游测试 16 个 Test 块失败：`Crypto routine failure`（NTOWF/NTHash/全部 GSSAPI 会话） | ohpcd openssl/3.0.21 是**静态包**，MD4 在 legacy provider；上游 `init_ossl3_ctx()` 虽显式 `OSSL_PROVIDER_load("legacy")`，但模块查找路径默认编译前缀（prefix=/ 家族 → `//ossl-modules` 不存在）→ `EVP_MD_fetch("MD4")` 返回 NULL | `OPENSSL_MODULES=<openssl 包>/lib/ossl-modules`：build() 注入（make check）+ package_info runenv（消费期）+ test_package 显式注入（ppp/2.5.2 先例） |
| 5 | `configure: error: cannot guess build type` | 设备 `uname -s = HarmonyOS`，config.guess（automake 2024-07-27）不识别 | 显式 `--build/--host=aarch64-unknown-linux-gnu`（build==host 仍走本地 conftest；止损先例 #1 形态 B） |
| 6 | `configure: error: Could not find OpenSSL support` | AX_CHECK_OPENSSL 先 `pkg-config openssl`（conan .pc 不在默认 PKG_CONFIG_PATH）再退固定前缀（设备全无）；最终链接测试的 LIBS 已被 configure.ac:69 覆写（无 -lssl） | `--with-openssl=<openssl 包目录>` 走该宏用户目录分支（头/库/-lssl -lcrypto 全由宏注入） |
| 7 | 模块留下 `u8_conv_to_encoding` 未解析（dlopen 必炸）、`ntlmssptest` 报 `undefined symbol: crc32` | configure.ac:69 `LIBS="$PTHREAD_CFLAGS $CFLAGS"` 是上游笔误（68 行刚收进依赖 -l 集合，69 行整体覆写）；Makefile.am 只把 `$(UNISTRING_LIBS)` 给 ntlmssptest，模块链接行（GN_MECHGLUE_LIBS 在 objects 之前）拿不到静态库（ohpcd libunistring/openssl 均静态） | make 命令行变量覆盖 `LIBS=...`（优先级最高、出现在 objects 之后，静态库可被抽取、零源码补丁）；值必须带显式引号（conan 拼参不转义，实测只留下 `LIBS=-pthread`） |
| 8 | 上游测试 8 个 Test 块失败：已建立上下文 `import_sec_context` 报 EINVAL | conan openssl `configuration.h: #define RC4_INT unsigned char`（RC4 状态 258B），而 `export_keys` 用 `sizeof(buf)`（258×4=1032B）序列化、导入按 `258*sizeof(RC4_INT)` 校验 → 1032≠258。Fedora 恰好 RC4_INT=unsigned int(4) 使两者相等才没暴露 | 补丁 0003：改写 `RC4_EXPORT` 实际写入的 `out.length` |
| 9 | `strerror_r` 编译错（int→char* 转换） | 上游变体守卫 `(POSIX… && !_GNU_SOURCE)` 是 glibc 中心假设：config.h 的 _GNU_SOURCE 让 musl（只有 XSI 变体）走进 GNU 分支 | 补丁 0002：按 `__GLIBC__` 判别，非 glibc 一律 XSI 分支 |
| 10 | 本地迭代早期：`LIBS=` 覆盖未生效、`aclocal` 找不到 `//share/aclocal-1.18` 等 | conan 拼接 make 参数不转义；conan 包装参数被 shim 绕过 | 见 #7 引号、#2 重定位参数 |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| `patches/0001-src-debug-secure_getenv-ohos.patch` | src/debug.c | 非 glibc/bionic 平台内联 secure_getenv 等价实现 |
| `patches/0002-src-gss_err-strerror_r-xsi.patch` | src/gss_err.c | strerror_r 变体守卫改按 `__GLIBC__` 判别 |
| `patches/0003-src-gss_serialize-rc4-export-length.patch` | src/gss_serialize.c | RC4 状态序列化用 `out.length`（RC4_EXPORT 实写字节数） |

## 依赖版本

- krb5/1.22.1（共享）、libunistring/1.0（静态）、openssl/3.0.21（静态）、zlib/1.3.1
- tool_requires：autoconf/2.72、automake/1.18、libtool/2.5.4（+ 传递 m4/1.4.19、perl/5.42.2）
- iconv：OHOS libc 自带（`iconv_open("UTF16LE","UTF-8")` 设备探针 rc=0，无需 libiconv）

## 验证结果

```bash
# 上游测试（conan create 内 make check，automake harness）
# TOTAL: 3  PASS: 3  FAIL: 0  SKIP: 0（ntlmssptest + tests/env1.sh + tests/env2.sh）
# 块级执行单元：46 Test 块 × 3 入口 = 138，全部 SUCCESS
grep -c 'Test: SUCCESS' <build>/ntlmssptest.log <build>/tests/env1.sh.log <build>/tests/env2.sh.log   # 46/46/46
# 消费者（test_package，鸿蒙特有）
GSSNTLM_PROBE_RESULT checks=20 fails=0
```

注：上游 `tests/env2.sh` 的退出码不反映 `ntlmssptest` 结果（脚本末尾只检查 trace 文件是否存在，
恒真分支吞掉 rc）——判读以块级计数与 harness 的 `PASS: ntlmssptest/env1` 为准，env2 的 46 块
`Test: SUCCESS` 单独核过。

## 注意事项

- **OPENSSL_MODULES（已知限制）**：模块静态链接 libcrypto，任何消费进程取 MD4(legacy) 都需
  `OPENSSL_MODULES=<openssl 包>/lib/ossl-modules`。conan 消费者经本包 `runenv_info` 自动获得；
  **非 conan 系统集成**（把 gssntlmssp.so 装进系统 GSSAPI）须自行设置该变量或在 openssl.cnf
  激活 legacy provider，否则 NTOWF/NTHash（口令→NT hash）路径失败。
- **krb5-config 输出失真**：conan 包装下 `krb5-config --cflags/--libs` 输出 `-I//include -L//lib`
  （prefix=/），其 `-L` 与 rpath 均不可用；本配方的真实 -I/-L 全部来自 AutotoolsDeps，
  运行期库解析靠 LD_LIBRARY_PATH（conanrun）。
- **GSSAPI loader 的模块发现面未覆盖（W4 轮1 P3 登记）**：真实集成里
  `libgssapi_krb5` 这类 loader 按 mech 配置（`$(sysconfdir)/gss` 一族）发现机制插件，
  上游 `make install` 并不安装 mech 配置文件，本配方也未导出模块搜索路径；
  test_package 直接 `dlopen` 安装树模块，**绕过了 loader 发现机制**——即
  「经 libgssapi_krb5 真实发现并加载 NTLMSSP」这条端到端路径本 PR 未覆盖。
  conan 消费者当前需自行提供 mech 配置或直接 dlopen/注册。
- **跨发行版 IPC token 不兼容（补丁 0003 引申）**：上下文导出 token 内嵌 RC4 状态长度取决于
  构建时 RC4_INT 宽度，不同 openssl 构建间不可互导（本就非线协议，仅进程间导出用）。
