# opendkim

## 简介
OpenDKIM 是 Trusted Domain Project 维护的 DKIM (DomainKeys Identified Mail)
实现：提供 `libopendkim` 签名/验证 C 库，以及密钥生成、签名测试等命令行工具。
邮件服务器通过它对出站邮件做 DKIM 签名、对入站邮件做 DKIM 验证，是反垃圾邮件/
反钓鱼体系 (DMARC) 的核心组件之一。

## OHOS 适配 (2.11.0-beta2)

- **版本**: 2.11.0-Beta2（上游 GitHub tag `rel-opendkim-2-11-0-Beta2`；
  SourceForge 最新官方发行包为 2.10.3，无 Beta2 发行包，故用 GitHub tag 源码）
- **构建系统**: autotools（GitHub tag tarball 不含 Makefile.in，构建时用
  `tool_requires automake/1.18 + libtool/2.5.4` 自举 libtoolize→aclocal→
  autoheader→automake→autoconf）
- **关键适配**:
  - E007: 显式 `--build/--host aarch64-unknown-linux-ohos`，避免跑不识别
    HarmonyOS 的 stock config.guess
  - E097: configure 临时目录 `umask 077 + ./confXXXXXX` 在 HMDFS setgid
    目录下被拦（config.status 写 subs1.awk Permission denied），配方内联改为
    `umask 022 + $TMPDIR/confXXXXXX`
  - musl libc 无 `_res` 全局变量（stub resolver）：`RES_USE_DNSSEC` 请求用
    `__GLIBC__` 守卫（patch 0001）
  - unbound conan 包的 `libunbound.la` 带 DESTDIR 烤死的 `//lib/libevent.la`
    死路径：`generate()` 构建 shim 前缀目录（静态库 + 重写 .la 的
    dependency_libs 指向真实传递依赖）
  - libbsd 不需要：musl libc 原生提供 strlcpy/strlcat，configure 的
    `AC_CHECK_FUNCS` 直接命中
- **功能配置**: 默认特性集 + `--enable-diffheaders`（tre）+ unbound DNSSEC
  解析；`--disable-filter`（milter 过滤守护进程需要完整 MTA 运行环境，
  库包范围外）；SQL/LDAP/Lua/memcached 等全部关闭（R1 参数最少化）

## 依赖

- openssl/3.5.6.1（与 unbound/1.22.0 的依赖版本一致，保持依赖图无冲突）
- libmilter/8.18.2
- tre/0.9.0
- unbound/1.22.0
- libevent/2.1.12、expat/2.8.2（unbound 静态库传递依赖，shim 需要）

## 命令行工具

`opendkim-genkey`（生成 DKIM 密钥对）、`opendkim-genzone`（生成 DNS 区文件）、
`opendkim-testkey`（测试密钥 DNS 发布）、`opendkim-testmsg`（测试消息签名）。

## 参考

- 官网: https://trusteddomainproject.org/
- 源码: https://github.com/trusteddomainproject/OpenDKIM
