# LWP::Protocol::https

## 简介

LWP::Protocol::https 为 LWP::UserAgent 提供 HTTPS 协议支持。它是 libwww-perl 的插件模块，安装后 LWP 可以访问使用 HTTP over SSL/TLS 的网站。

## 功能概述

- 为 LWP::UserAgent 添加 HTTPS 协议处理能力
- 支持主机名验证和证书验证
- 支持 CONNECT 代理隧道
- 提供 SSL 连接信息（证书、协议版本、加密套件）

---

## OHOS 适配

### 适配要点

1. **纯 Perl 模块**：无 XS 组件，编译简单
2. **依赖链完整**：需要完整的 HTTPS 依赖链才能运行
3. **SELinux 限制**：XS 模块（Net::SSLeay）受 HMDFS 限制

### 已知问题

#### ⚠️ SELinux HMDFS 限制（关键问题）

XS 模块无法从用户目录加载：

| 文件位置 | SELinux type | 加载结果 |
|---------|-------------|----------|
| `/data/service/hnp/perl.org/perl_5.42.0/lib` (系统目录) | `hnp_file:s0` | ✅ 可加载 |
| `~/usr/local/lib` (用户目录，HMDFS) | `hmdfs:s0` | ❌ Permission denied |

**根因**：`hishell_hap` SELinux domain 只能加载 `hnp_file` 类型文件

**影响范围**：
- Net::SSLeay（XS 模块）无法从 `~/usr/local/lib` 加载
- IO::Socket::SSL（纯 Perl）依赖 Net::SSLeay，无法工作
- LWP::Protocol::https 整个依赖链断裂

### 与 Linux 的差异

| 方面 | Linux | OpenHarmony |
|------|-------|-------------|
| 模块编译 | 标准 | 需特殊链接参数 |
| XS 模块加载 | ✅ 任意目录 | ❌ 仅系统目录 |
| 纯 Perl 模块 | ✅ | ✅ 无差异 |

---

## 排除与替代

### 无 PurePerl 替代方案

LWP::Protocol::https 没有纯 Perl 替代方案，必须依赖 Net::SSLeay XS 模块。

### 与 perl-dbd-pg 对比

| 模块 | XS 模块 | PurePerl 替代 | 解决方案 |
|------|---------|---------------|----------|
| perl-dbd-pg | DBI/Pg.so | ✅ DBI::PurePerl | HNP 包 + PurePerl |
| LWP-Protocol-https | Net::SSLeay | ❌ 无 | HNP 包安装 |

---

## 依赖

### 编译依赖

- perl (5.8.1+)
- ExtUtils::MakeMaker

### 运行依赖

| 模块 | 最低版本 | 编译状态 | 加载状态 | 说明 |
|------|---------|---------|---------|------|
| IO::Socket::SSL | 1.970 | ✅ 已编译 | ❌ SELinux | 纯 Perl，依赖 Net::SSLeay |
| Net::HTTPS | 6 | ✅ 已编译 | ✅ 可用 | 来自 Net::HTTP 6.23 |
| LWP::UserAgent | 6.06 | ✅ 已编译 | ✅ 可用 | 来自 perl-libwww 6.81-r0 |
| LWP::Protocol::http | - | ✅ 已编译 | ✅ 可用 | 来自 perl-libwww 6.81-r0 |
| Net::SSLeay | - | ✅ 已编译 | ❌ SELinux | XS 模块，需系统目录 |

### 可选依赖

- Mozilla::CA：提供默认 CA 证书（未编译）

---

## 解决方案

### 方案 1：HNP 包安装（推荐）

将 Net::SSLeay 安装到系统 Perl 目录：

```bash
# 1. 创建 HNP 包
cd ~/usr/local/lib/site_perl/5.42.0
tar -czf ~/tmp/net-ssleay.hnp \
    aarch64-linux/auto/Net/SSLeay/SSLeay.so \
    aarch64-linux/Net/SSLeay.pm \
    Net/SSLeay.pm \
    Net/SSLeay.pod

# 2. 安装到系统目录（需要管理员权限）
sudo -u installs unzip ~/tmp/net-ssleay.hnp \
    -d /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/

# 3. 重新签名（获得正确的 SELinux type）
/data/service/hnp/bin/binary-sign-tool sign \
    -inFile /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Net/SSLeay/SSLeay.so \
    -outFile /tmp/SSLeay.so.signed \
    -selfSign 1

# 4. 替换签名文件
sudo -u installs mv /tmp/SSLeay.so.signed \
    /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Net/SSLeay/SSLeay.so

# 5. 同样处理 IO::Socket::SSL（纯 Perl，直接复制）
sudo -u installs cp -r ~/usr/local/lib/site_perl/5.42.0/IO \
    /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/
```

### 方案 2：等待预编译包

等待 Net::SSLeay 和 IO::Socket::SSL 预编译包发布到 cmd-pkgs 仓库。

```bash
# 从 cmd-pkgs 安装（发布后）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | \
    sh -s -- Net-SSLeay 1.85
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | \
    sh -s -- IO-Socket-SSL 2.085
```

---

## 功能验证

### 当前验证状态

```perl
# 测试 Net::SSLeay（当前失败）
perl -MNet::SSLeay -e 'print $Net::SSLeay::VERSION'
# 输出: Permission denied (SELinux HMDFS 限制)

# 测试 IO::Socket::SSL（当前失败）
perl -MIO::Socket::SSL -e 'print $IO::Socket::SSL::VERSION'
# 输出: 依赖 Net::SSLeay 加载失败

# 测试 LWP::Protocol::https（当前失败）
perl -MLWP::Protocol::https -e 'print $LWP::Protocol::https::VERSION'
# 输出: 依赖链断裂
```

### HNP 安装后验证

```perl
# 测试 Net::SSLeay（HNP 安装后）
perl -MNet::SSLeay -e 'print $Net::SSLeay::VERSION'
# 预期输出: 1.85

# 测试 IO::Socket::SSL
perl -MIO::Socket::SSL -e 'print $IO::Socket::SSL::VERSION'
# 预期输出: 2.085

# 测试 HTTPS 请求
use LWP::UserAgent;
$ua = LWP::UserAgent->new(ssl_opts => { verify_hostname => 0 });
$res = $ua->get("https://www.example.com");
print $res->status_line;
# 预期输出: 200 OK
```

---

## Net::SSLeay 编译要点

### 编译环境

- OpenSSL: 系统 OpenSSL 3.0.9 (`/usr/bin/openssl`)
- 编译器: clang
- 需要链接本地编译的 libssl/libcrypto

### 编译命令

```bash
# 1. 配置
OPENSSL_PREFIX=/usr PERL_MM_USE_DEFAULT=1 perl Makefile.PL \
    PREFIX=~/usr/local \
    INC="-I~/usr/local/include" \
    LDDLFLAGS="-shared -nostartfiles -nodefaultlibs"

# 2. 修改链接库路径（Makefile）
EXTRALIBS = -L~/usr/local/lib -lssl -lcrypto ~/usr/local/lib/libz.a
LDLOADLIBS = -L~/usr/local/lib -lssl -lcrypto ~/usr/local/lib/libz.a -lc -lm

# 3. 编译
make

# 4. ELF 签名（必需）
/data/service/hnp/bin/binary-sign-tool sign \
    -inFile blib/arch/auto/Net/SSLeay/SSLeay.so \
    -outFile ~/tmp/SSLeay.so.signed \
    -selfSign 1

# 5. 安装
cp ~/tmp/SSLeay.so.signed ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Net/SSLeay/SSLeay.so
cp -r blib/lib/Net ~/usr/local/lib/site_perl/5.42.0/
```

### 编译产物

- SSLeay.so: 505KB（已签名）
- Net/SSLeay.pm: 主模块
- Net/SSLeay.pod: 文档

---

## 参考

- 源码仓库: https://github.com/libwww-perl/LWP-Protocol-https
- CPAN: https://metacpan.org/pod/LWP::Protocol::https
- Net::SSLeay: https://metacpan.org/pod/Net::SSLeay
- IO::Socket::SSL: https://metacpan.org/pod/IO::Socket::SSL
- perl-dbd-pg 测试报告: 参考其 XS 模块 SELinux 解决方案