# openconnect 8.10 适配笔记

## 构建信息
- 构建系统：autotools（官方 release tarball 自带 configure + config.guess/config.sub）
- 交叉编译：clang 15.0.4，--host=aarch64-unknown-linux-ohos（显式指定，tarball 的 config.guess 2018 版不识别 HarmonyOS）
- 上游源：https://www.infradead.org/openconnect/download/openconnect-8.10.tar.gz
  sha256 30e64c6eca4be47bbf1d61f53dc003c6621213738d4ea7a35e5cf1ac2de9bab1
- ⚠️ GitHub tag 归档 (v8.10.tar.gz) 无预生成 configure，需 autogen.sh + automake/libtoolize ——
  构建机只有 autoconf 2.72（无 automake/libtoolize），不可用；必须用官方 release tarball

## W0 依赖实测（2026-09-02，conan download -r=ohpcd --only-recipe）
- gnutls/3.8.10 EXISTS（传递 nettle/hogweed、libtasn1/4.21.0、libgcrypt/1.11.0、
  libgpg-error/1.55、gmp/6.3.0、libunistring/1.0）
- libxml2/2.15.3 EXISTS（configure 无条件 PKG_CHECK_MODULES(libxml-2.0)，硬依赖）
- zlib/1.3.1 EXISTS（zlib 在 configure 有 -lz fallback，但制品仓有就用 conan）
- lz4/1.10.0 EXISTS 但 --without-lz4（可选压缩，减少依赖面）
- stoken/0.93 → conan download 报 "error:system acceleration policy not enabled"（制品仓无此包）→ --without-stoken
- libproxy/0.4.18 → 同上缺失 → --without-libproxy
- krb5/1.21.3（gssapi）→ 缺失 → --without-gssapi
- libpskc/2.2.0 → 缺失 → --without-libpskc
- libpcsclite → 缺失（Yubikey 支持，可关）→ --without-libpcsclite
- java → --without-java（JNI 绑定，不适用）

## configure 参数（R1 最少化 + 必要 --without）
```
--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos
--with-vpnc-script=/etc/vpnc/vpnc-script   # 发行版打包标准做法（绕过构建机路径检查）
--disable-shared --disable-symvers          # application 包：只出可执行文件；symvers 见踩坑2
--without-lz4 --without-libproxy --without-stoken --without-libpcsclite
--without-libpskc --without-gssapi --without-java
```

## 踩坑记录
1. **linux/tcp.h 冲突**：OHOS musl 的 <linux/tcp.h> 链入 <linux/socket.h>，
   其中 struct sockaddr_storage 与 <sys/socket.h> 重定义（glibc 无此问题，linux/socket.h 有 include guard）
   → patch 0001：cstp.c/gpst.c 在 __OHOS__ 下改用 <netinet/tcp.h>（TCP_INFO 宏 + struct tcp_info 均有）
2. **libtool 引号损坏**：tarball 的 ltmain.sh (libtool 2.4.6 时代) 与 autoconf 2.72 生成的
   config.status 转义不兼容——old_archive_cmds/archive_cmds 等模板变量在双引号赋值里提前展开
   （$AR→"ar" 展开正常但 $oldobjs 为空 → "ar cru" 无参数；install 模式 "chmod 644" 无文件名）
   → conanfile `_fix_libtool_quoting()` 把损坏赋值改回单引号；ECHO="print -r --"（ksh）→ printf
   → --disable-symvers 使 archive_expsym_cmds 不被使用（该赋值损坏最严重，直接置空）
3. **config.status umask**：`(umask 077 && mktemp -d "./confXXXXXX")` 在 HMDFS 上 0700 临时目录
   导致 subs1.awk Permission denied（cattle/opensp/ncurses 先例）→ `_fix_config_status()` 去掉 umask
4. **依赖 .la 残留路径**：ohpcd 二进制包构建时 prefix=/，.la 里 libdir='//lib'、
   dependency_libs 指向过期包目录 → libtool 链接报 "not a valid libtool archive"（cattle CI#16082 先例）
   → `_fix_dependency_la_paths()` 重写 libdir + 跨包引用
5. **musl stdlib.h**：glibc 下 stdio.h 等会间接引入 stdlib.h，musl 不会 → auth.c/auth-globalprotect.c/
   gnutls_tpm*.c/iconv.c/lzo.c 隐式声明 malloc/calloc/free/exit/setenv/mkstemp/atoi
   被上游 -Werror-implicit-function-declaration 拦截 → patch 0002 显式补 include（8 个文件）
6. **make -j2 问题**：OHOS 沙箱无 mkfifo（automake jobserver）→ 一律 -j1
7. **ELF 签名**：sbin/openconnect 需 binary-sign-tool sign -selfSign 1 后才能执行
8. **lib.a 名字错误**：损坏的 libname 逻辑在 --disable-shared 下产出 lib.a（应 libopenconnect.a）；
   application 包不发布库文件，package() 里剔除即可

## 上游测试
- `make check`：3/3 PASS（tests/Makefile.am 注册）
  - autocompletion：bash 补全脚本，执行构建出的 openconnect 解析参数（需 LD_LIBRARY_PATH 带依赖库）
  - lzstest：LZS 解压 C 单元测试
  - seqtest：ESP 序列号重放窗口 C 单元测试
- tests/scripts/ 下未注册进 check_PROGRAMS 的测试（约 20+ 个）：需 ocserv 测试服务器 + softhsm2
  PKCS#11 令牌 + DTLS 服务端 + root netns，conan 沙箱内不可运行（依赖外部测试基础设施，FAQ #18 路径 B）
  - 具体分类：auth-*（PKCS#11 认证流，需 softhsm2+证书链）、bad_dtls/dtls-psk（需服务端）、
    cert-fingerprint/serverhash（需在线 VPN 服务器）、sigterm（需 root + tun）
- 设备运行验证：openconnect --version 输出
  "OpenConnect version v8.10-unknown / Using GnuTLS 3.8.10. Features present: HOTP software token,
   TOTP software token, System keys, DTLS, ESP / Supported protocols: anyconnect (default), nc, gp, pulse"

## 产物
- bin/openconnect（从 sbin/libexec 归一化到 bin/）
- include/openconnect.h（libopenconnect API，下游集成用）
- lib/pkgconfig/openconnect.pc
---

**编译结束**: 2026-09-02 18:52
**最终状态**: published
