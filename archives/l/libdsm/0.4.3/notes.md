# libdsm 0.4.3 — 编译笔记

## 上游事实（实测，修正任务卡过时信息）

- 上游 0.4.3 已从 autotools 切换为 **meson**（tarball 只含 meson.build /
  meson_options.txt，无 configure/autogen.sh）。任务卡所述"bootstrap/autogen"路线不适用。
- 真实依赖是 **libtasn1**（`dependency('libtasn1')`，SPNEGO/NTLM 认证的 ASN.1 解析），
  不是 zlib——全源码树 grep 无任何 zlib 引用。zlib 未声明、未使用、未依赖。
- 可选依赖 libgcrypt/openssl：0.4.3 的 meson.build 里**不存在**（那是 libdsm 0.3.x
  时代 autotools 的可选项），无需关闭。
- tarball 不含预生成的 spnego_asn1.c：构建时需 `asn1Parser` 从
  contrib/spnego/spnego.asn1 生成（上游 dist_generated.py 就是干这个的）。

## 平台探测结论（全部本机实测，2026-10-09）

| 探测项 | 结果 | 影响 |
|---|---|---|
| iconv_open (musl libc) | OK（r=0 转码成功） | 无需第三方 libiconv，meson 探测直接通过 |
| getifaddrs / nl_langinfo / sys/queue.h（严格 C11+POSIX2008） | 全部声明可见 | HAVE_GETIFADDRS 等宏正确置位，netbios_ns 走 getifaddrs 枚举路径 |
| strlcpy（严格 POSIX 方言） | **未声明**（隐式声明告警） | meson 探测会判 false → 编进上游 compat/strlcpy.c——无害但多余 |
| strlcpy（gnu11 + _GNU_SOURCE） | 声明可见 | musl 原生 strlcpy 直接用 |
| NetBIOS UDP 序列（SO_BROADCAST/IP_MULTICAST_LOOP/bind:0） | 全部成功 | netbios_ns_new() 在 OHOS 可完整初始化 |
| TCP 非阻塞 connect 127.0.0.1:445 + select + SO_ERROR | ECONNREFUSED(111) 立即传播 | connect 错误路径可用作测试判据，不挂死 |

## 适配方案（零源码 patch）

1. `c_std=gnu11`（上游默认 c11）+ native file `[properties] c_args=['-D_GNU_SOURCE']`
   ——根因：meson.build 对非 linux/darwin 系统统一 `add_project_arguments('-D_POSIX_C_SOURCE=200809L')`，
   严格 POSIX 方言下 musl 不声明 strlcpy；注入 _GNU_SOURCE 后全声明可见（dav1d 同族手法）。
2. `binaries=false`：关闭 bin/ 下 4 个示例工具（dsm/discover/inverse/lookup），纯库包。
3. `wrap_mode=nodownload`：禁止 meson 私下下 wrap，依赖一律走 conan。
4. spnego_asn1.c 生成：`tool_requires("libtasn1/4.21.0")`（制品仓包自带 bin/asn1Parser
   + lib/libtasn1.so.6，实测 `asn1Parser -o spnego_asn1.c -n spnego_asn1_conf
   contrib/spnego/spnego.asn1` 成功，产物 2228 字节）。
   conan 的 tool_requires 会把 libtasn1 的 bin/ 与 lib/ 同时注入构建环境 PATH 与
   LD_LIBRARY_PATH（buildenv），meson 的 `find_program('asn1Parser')` 可命中。
5. 签名：package() 内 _sign_binaries() 对 lib/**/*.so 重签（本仓通行手法）。

## 依赖链（W0 核验）

- libtasn1/4.21.0：制品仓已发布（recipe revision 48e142678b8738090c34b32176b8516e）
- zlib：**非依赖**（任务卡信息过时）
- threads / iconv：musl libc 原生，无 conan 包

## 测试

上游 0.4.3 无测试套件（无 tests/ 目录、无 test 选项、无 make check 对应物；
唯一可执行物是 bin/ 下 4 个需要真实 SMB 服务器/局域网的示例工具，已随 binaries=false 关闭）。
适配后 test_package 用 8 项断言做消费者级验证（真实 API 生命周期 + socket 行为），
判据设计见 test.c 头注释——每个断言都对应"证明这不是桩实现"的反空壳逻辑。
