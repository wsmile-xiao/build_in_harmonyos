# dcc-extras

## 简介

**DCC（Distributed Checksum Clearinghouse）** 是基于校验和（checksum）的分布式
反垃圾邮件系统，由 Rhyolite Software / Vernon Schryver 维护。
本包 `dcc-extras` 对应 DCC 同一源码 tarball 的**客户端 + 服务端 + 辅助/测试工具全集**
（cdcc、dccproc、dccif-test、dccd、dccifd、dbclean、dblist、dccsight、ck2ip、
dump-clients、dns-helper、wlist、cgi-bin、libexec 脚本），即上游 `make` 的默认构建集合。

- 上游项目页：<https://www.dcc-servers.net/dcc/>
- 官方发行文件：`https://www.dcc-servers.net/dcc/source/dcc.tar.Z`（compress(1) `.Z`）
- 本包版本：**2.3.169**（2024-03-22，与上游版本号一致）

## 关键信息

| 项 | 值 |
|---|---|
| 语言 | C（93 个 `.c` + 21 个 `.h`；Perl/shell 脚本为辅助） |
| 构建系统 | autotools（自带 autoconf-2.13 风格 `configure`） |
| 运行时依赖 | 仅系统库（libc/musl、libm；同源树内 libdcc/libclnt/libthr/libsrvr 静态库） |
| 编译期第三方依赖 | 无（libmilter 缺席时 dccm 不构建，属上游设计） |
| 上游测试 | **无自动化测试套件**（见 `2.3.169/reports/test-report.md`） |
| OHOS 适配 | 1 处源码补丁：`include/dcc_types.h` 补 `#include <sys/types.h>` |

## 包内容

```
bin/        cdcc、dccproc、dccif-test          （用户命令）
libexec/    dccd、dccifd、dbclean、dblist、dccsight、ck2ip、dump-clients、
            dns-helper、wlist、check_ip_range、fix-map 及 start-dccd/updatedcc 等脚本
cgi-bin/    Perl CGI（list-msg、chgpasswd、edit-whiteclnt 等）
include/    DCC 公共头文件（dcc_defs.h/dcc_clnt.h/…）
lib/        libdcc.a、libclnt.a（同源树内静态库；上游称 libdcc 为
            "the public DCC client library"）
res/dcc/    上游静态配置原型（flod、whitelist、whiteclnt、dcc_conf、map.txt 等）
licenses/   LICENSE
```

## 版本

| 版本 | 状态 | 日期 |
|---|---|---|
| 2.3.169 | built | 2026-09-26 |
