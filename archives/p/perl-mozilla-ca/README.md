# Mozilla::CA 20250602 for HarmonyOS

## 概述

Mozilla::CA 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

Mozilla::CA 是一个 Perl 模块，提供 Mozilla 的 CA 根证书包 (cacert.pem)，用于 SSL/TLS 连接时的证书验证。它是纯 Perl 模块，不包含 C/XS 代码。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | perl-mozilla-ca |
| 版本 | 20250602-r0 |
| 下载地址 | https://cpan.metacpan.org/modules/by-module/Mozilla/Mozilla-CA-20250602.tar.gz |
| 官方文档 | https://metacpan.org/pod/Mozilla::CA |
| 许可证 | MPL-2.0 |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | N/A（纯 Perl 模块，无 C 编译） |
| Perl 版本 | 5.42.0 |
| 构建系统 | perl-makefile-pl (ExtUtils::MakeMaker) |

## 编译步骤

```bash
# 1. 下载源码（init-build 下载失败时使用 curl 替代）
curl -o Mozilla-CA-20250602.tar.gz https://cpan.metacpan.org/modules/by-module/Mozilla/Mozilla-CA-20250602.tar.gz

# 2. 解压
tar xzf Mozilla-CA-20250602.tar.gz
cd Mozilla-CA-20250602

# 3. 生成 Makefile
perl Makefile.PL PREFIX=$HOME/usr/local

# 4. 编译（纯 Perl 模块，仅 cp 文件到 blib）
make

# 5. Staging 安装
make install DESTDIR=$HOME/tmp/test-install-perl-mozilla-ca-20250602-r0

# 6. 测试
make test

# 7. 正式安装
make install
```

## 补丁说明

无补丁。纯 Perl 模块，无需修改源码即可在鸿蒙平台编译。

## 遇到的问题

### 问题1: init-build 下载失败

**现象**: `ohc-run.py init-build` 下载源码时 SSL 证书验证失败

**原因**: Python urllib 的 SSL 证书链在鸿蒙平台不完整

**解决**: 使用 curl 手动下载到本地，用 `file://` URL 重新初始化

### 问题2: make check 无此目标

**现象**: 脚本尝试运行 `make check` 时报错 `No rule to make target 'check'`

**原因**: Perl 模块使用 `make test` 而非 `make check` 进行测试

**解决**: 使用 `make test` 替代 `make check`

## 测试结果

详见 [test-report.md](./20250602-r0/reports/test-report.md)

| 测试项 | 结果 |
|--------|------|
| 模块加载与版本 | ✅ |
| SSL_ca_file() 函数 | ✅ |
| CA 证书 PEM 格式完整性 | ✅ |
| 证书数量 (143 个 CA) | ✅ |
| 预编译包完整性 | ✅ |
| make test | ✅ PASS |
| IO::Socket::SSL 集成 | ⚠️ 平台限制（Net::SSLeay.so SELinux） |

## 验证安装

```bash
# 检查模块版本
perl -MMozilla::CA -e 'print $Mozilla::CA::VERSION'
# 输出: 20250602

# 检查 CA 证书文件路径
perl -MMozilla::CA -e 'print Mozilla::CA::SSL_ca_file()'
# 输出: /storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/Mozilla/CA/cacert.pem

# 检查证书数量
grep -c "BEGIN CERTIFICATE" $(perl -MMozilla::CA -e 'print Mozilla::CA::SSL_ca_file()')
# 输出: 143
```

## 安装产物

| 文件 | 路径 | 大小 |
|------|------|------|
| CA.pm | lib/site_perl/5.42.0/Mozilla/CA.pm | ~3KB |
| cacert.pem | lib/site_perl/5.42.0/Mozilla/CA/cacert.pem | ~222KB |

## 经验总结

1. 纯 Perl 模块编译简单，无需 C 编译器或特殊链接参数
2. 鸿蒙平台 Python urllib SSL 证书链不完整，下载 CPAN 源码时需用 curl 替代
3. Perl 模块使用 `make test` 而非 `make check`，需要在编译流程中适配
4. SELinux HMDFS 限制不影响纯 Perl 模块加载，仅影响 XS 模块（.so 文件）
5. Mozilla::CA 提供的 CA 证书包可用于 HTTPS 请求验证，是 LWP/IO::Socket::SSL 等模块的依赖

## 参考资料

- [Mozilla::CA CPAN 文档](https://metacpan.org/pod/Mozilla::CA)
- [Mozilla CA 证书政策](https://www.mozilla.org/en-US/about/governance/policies/security-group/certs/)
