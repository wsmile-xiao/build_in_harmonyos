# nrpe 4.1.3 HarmonyOS PC 适配笔记

## 概述
- 软件：NRPE 4.1.3（Nagios Remote Plugin Executor，远端监控代理：nrpe daemon + check_nrpe 客户端，纯 C，autotools）
- 上游：https://github.com/NagiosEnterprises/nrpe（tag nrpe-4.1.3，2024-12-10）
- 适配路径：archives/n/nrpe/4.1.3/
- 构建目标：aarch64-linux-ohos（OpenHarmony / HarmonyOS PC，clang 15 交叉编译）
- sha256：5a86dfde6b9732681abcd6ea618984f69781c294b8862a45dfc18afaca99a27a（GitHub asset 与 Homebrew formula 双源核对一致，本地计算复核）

## 依赖与配置决策
| 项 | 决策 | 依据 |
|---|---|---|
| openssl | conan requires openssl/3.5.8.1，`--with-ssl=<prefix> --with-ssl-inc --with-ssl-lib` 显式路径 | 硬依赖（SSL 加密传输）；ohpcd 已发布（conan download 实证）；指定 ssl-inc/ssl-lib 后 AX_NAGIOS_GET_SSL 走显式路径搜索（Homebrew 同款："Set both or it still looks for /usr/lib"）；依赖注入走 build_folder 私有 prefix（R49，参考 asterisk-srtp） |
| tcp wrappers | `--disable-tcpd` | libwrap 未发布 ohpcd；tcpd 默认 optional，显式禁用裁剪（任务要求） |
| gnutls/nss | 不用 | --with-ssl-type 默认 openssl |
| Kerberos | 不配 | 检测未命中仅 WARN 不阻塞 |
| 用户/组 | `--with-nrpe-user/--with-nrpe-group/--with-nagios-user/--with-nagios-group=<当前构建用户>` | NRPE_INSTALL_OPTS="-o nrpe_user -g nrpe_group" 默认 nagios（OHOS /etc/passwd 无 nagios，普通用户 chown 失败）；Homebrew 同样用当前用户 |
| 路径 | `--with-piddir/--with-logdir/--with-pipedir=<私有prefix>/var/*`、`--libexecdir=<私有prefix>/libexec`、`--sysconfdir=<私有prefix>/etc` | ax_nagios_get_paths 把未显式设置的 libexecdir 强制改写为 /usr/nagios；install-daemon 会 mkdir piddir——全部指向私有路径避免系统目录权限问题 |
| 功能开关 | `--enable-ssl --enable-command-args` | SSL 默认 check 但显式启用；command-args 允许客户端指定命令（Homebrew 同款） |
| DH | 默认 need_dh=yes（AUTO_SSL_DH，openssl 3.x 用 SSL_CTX_set_dh_auto 内置 DH） | 无需外部 openssl 二进制生成 dh.h；conftest 版本探测在本机/CI（同为 aarch64 OHOS）可运行 |

## 遇到的问题与解决方案
| # | 问题 | 现象 | 解决方案 |
|---|---|---|---|
| 1 | config.sub 不识别 ohos | `./config.sub aarch64-linux-ohos` → system 'ohos' not recognized | patches/0001-config.sub-ohos.patch：两处加 `linux-ohos*`（KERNEL-OS 组合段 + basic OS 类型段），社区标准写法（aalib 同款） |
| 2 | config.guess 无法识别 HarmonyOS | uname -s=HarmonyOS → unable to guess system type | 显式 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos` 跳过探测（config.sub 已 patch 支持） |
| 3 | HMDFS umask 077 | configure 内 4 处 `umask 077 && mktemp -d "./confXXXXXX"`，HMDFS 权限问题 | patches/0002-configure-umask.patch：4 处 umask 077 → 022（ngircd 2 处/asterisk 同款问题，nrpe 共 4 处） |
| 4 | libexecdir 被强制改写 | 未显式设置时 ax_nagios_get_paths 把 libexecdir 改为 /usr/nagios | 显式 `--libexecdir=<私有prefix>/libexec` |
| 5 | install -o nagios 失败 | NRPE/NAGIOS_INSTALL_OPTS 默认 -o nagios -g nagios，普通用户无法 chown 不存在用户 | `--with-*-user/group=<当前用户>`（与 Homebrew 一致） |
| 6 | daemon 拒绝 root / 用户不存在 | check_privileges 拒绝 root；drop_privileges 需 getpwnam(nrpe_user) | 冒烟配置 nrpe_user/group=当前真实用户（非 root） |

## 测试设计
- 上游：无接入构建的自动化测试（仓库无 make check 目标；test-wrapper→travis-test-1 为 Travis 时代独立脚本，注释自述 "Replace this once test is working properly"，且需 root + nagios 系统用户 + /usr/local/nagios 路径，OHOS 沙箱不可执行）→ 如实计 0
- test_package 冒烟三件套：
  1. `nrpe -V`：版本输出断言（含 "NRPE" 与 "4.1.3"）
  2. `nrpe -f -n -c <最小配置>` 绑定 127.0.0.1 高位端口（allowed_hosts=127.0.0.1 + command[check_echo] 定义）+ `check_nrpe -H 127.0.0.1 -p PORT -n` 连通断言（daemon 版本响应）
  3. `check_nrpe -c check_echo` 远端命令执行断言（echo ok），随后 SIGINT/TERM 正常 shutdown

## 已知限制
- 无头环境冒烟使用 no-SSL 模式（-n），SSL 证书双向认证路径未覆盖（需证书文件）；SSL 编译与 DH 逻辑已启用（--enable-ssl，AUTO_SSL_DH）
- 上游无自动化测试套件可跑（travis-test-1 占位），冒烟由 test_package 承担
- 交叉编译产物为 OHOS ELF，仅能在 OHOS/鸿蒙 PC 环境运行（本机即目标平台）