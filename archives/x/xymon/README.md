# xymon

xymon（原 Hobbitmon）是一个网络/主机/服务监控系统，提供集中式可用性监测、阈值告警（红/黄/绿状态页）、趋势图形（RRD）与 Web 报表界面。

## 功能概述

- 主机与服务可用性监测（网络探测：conn/http/ldap/dns 等）
- 内置 `xymonping`（ICMP 实现）替代外部 fping 进行 ping 探测
- `xymond` 系列守护进程：状态收集、告警、历史存储、RRD 趋势
- CGI Web 界面（状态页、历史、图形、确认告警等 30+ 个 CGI）
- `bb`/`bbcmd` 客户端工具集与 `xymondigest` 摘要工具

## OHOS 适配要点

- 构建系统为上游自带 `configure.server`（交互式 shell 脚本，非 autoconf），通过 stdin 重定向非交互完成配置
- OHOS 不支持 shebang 直接执行：`build/*.sh`、`configure*` 删除首行 `#!/bin/sh` 后用 `bash` 显式调用
- 平台判定钉死为 `build/Makefile.Linux`（`uname -s` 在 OHOS 返回 HarmonyOS）
- 交叉编译探测程序（`test-endianness`、`build/test-*.c`、`lfs.sh`）无法在构建机运行，探测结论直接写入 `include/config.h`
- OHOS libc 无 `getrpcbyname()`：`xymonnet.c` 以 `#ifdef OHOS` 提供桩实现；RPC 头/库使用 libtirpc
- `build/Makefile.Linux` 在未定义 `PKGBUILD` 时产生空 `RPATH=-Wl,--rpath,`，会吞掉链接行后续参数——已注入 `PKGBUILD=yes` 并显式清空 `RPATH/RPATHOPT`
- rrdtool 1.9 的 `rrd_graph()` 为 8 参数 API，需定义 `RRDTOOL12`
- 全部 170 个 ELF 已用 `binary-sign-tool -selfSign 1` 自签名
- 上游 tarball 内 31 个符号链接（`xymond/webfiles/*_footer`）已物化为普通文件（HMDFS 符号链接不可靠）

## 依赖关系

| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1.1 | HTTP 压缩 |
| pcre | 8.45 | 正则 |
| libtirpc | 1.3.7 | RPC 头/库（替代 glibc sunrpc） |
| openssl | 3.5.8.1 | TLS |
| c-ares | 1.34.6 | 异步 DNS |
| openldap | 2.6.7 | LDAP |
| rrdtool | 1.9.0 | 图形/趋势数据 |

## 构建与验证

```bash
conan create archives/x/xymon/4.3.30 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

test_package 验证：`xymon --version` / `bbcmd --version` 输出 `Xymon version 4.3.30`；`xymondigest md5/sha256` 端到端摘要正确；包装布局（`bin/`、`libexec/`、`server/`、`etc/`、`www/`）完整。

## 已知限制

- 服务端运行时需要 `xymon` 系统用户与 `/var` 目录结构，本包仅提供安装产物，不创建系统用户，配置由使用方按需设置。
- 上游 4.3.30 无单元测试套件（无 `tests/` 目录、无 `check:`/`test:` 目标），`build/Makefile.test-*` 仅为 configure 阶段特性探测。
