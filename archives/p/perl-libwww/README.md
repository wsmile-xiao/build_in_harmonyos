# perl-libwww

Perl LWP (Library for WWW in Perl) - HTTP/HTTPS 客户端库

## 简介

libwww-perl (LWP) 是 Perl 的 HTTP/HTTPS 客户端库，提供 Web 内容获取、表单提交、HTTP 认证等功能。

## 核心功能

- **LWP::UserAgent**: HTTP/HTTPS 用户代理
- **LWP::Simple**: 简化 HTTP 操作接口
- **LWP::Protocol**: 协议处理框架
- **HTTP::Request/Response**: HTTP 消息处理

## 版本信息

- 当前版本: 6.81-r0
- 模块类型: 纯 Perl（无 XS 代码）
- 编译状态: published

## 依赖模块

| 模块 | 版本 | 类型 | 说明 |
|------|------|------|------|
| Clone | 0.46 | 纯 Perl | 对象克隆 |
| URI | 5.28 | 纯 Perl | URI 解析 |
| HTTP::Message | 6.46 | 纯 Perl | HTTP 消息 |
| Net::HTTP | 6.23 | 纯 Perl | HTTP 协议 |
| Try::Tiny | 0.31 | 纯 Perl | 异常处理 |
| IO::HTML | 1.004 | 纯 Perl | HTML 文件 |
| HTTP::Date | 6.06 | 纯 Perl | 日期处理 |
| LWP::MediaTypes | 6.04 | 纯 Perl | MIME 类型 |
| Encode::Locale | 1.05 | 纯 Perl | 编码本地化 |

## 鸿蒙平台适配

### SELinux HMDFS 限制
Clone 模块 XS 版本受 SELinux 限制无法加载，已使用纯 Perl 版本替代。

### 环境变量设置
使用前需设置 PERL5LIB 环境变量：
```bash
export PERL5LIB="$HOME/usr/local/lib/site_perl/5.42.0:$HOME/usr/local/lib/5.42.0"
```

### HTTPS 支持

HTTPS 协议需额外安装以下模块：

| 模块 | 类型 | 状态 |
|------|------|------|
| LWP::Protocol::https | 纯 Perl | ✅ 已编译 |
| IO::Socket::SSL | 纯 Perl | ✅ 已编译 |
| Net::SSLeay | XS | ⚠️ SELinux 限制 |

**重要说明**：Net::SSLeay 是 XS 模块，在鸿蒙平台受 SELinux HMDFS 限制，需要管理员安装到系统目录才能启用 HTTPS。

管理员操作步骤：
```bash
# 安装 Net::SSLeay XS 模块到系统目录
mkdir -p /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Net/SSLeay
cp ~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Net/SSLeay/SSLeay.so \
   /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Net/SSLeay/

# 安装纯 Perl SSL 模块
cp -r ~/usr/local/lib/site_perl/5.42.0/IO/Socket/SSL* \
      /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/IO/Socket/
cp ~/usr/local/lib/site_perl/5.42.0/LWP/Protocol/https.pm \
   /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/LWP/Protocol/
```

## 使用示例

### HTTP GET
```perl
use LWP::Simple;
my $content = get("http://example.com");
print $content;
```

### LWP::UserAgent
```perl
use LWP::UserAgent;
my $ua = LWP::UserAgent->new;
my $response = $ua->get("http://example.com");
print $response->status_line, "\n";
```

## 安装方法

### 预编译包安装
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-libwww 6.81-r0
```

### 手动安装依赖
如果预编译包未包含依赖模块，需手动安装：
```bash
# 下载依赖模块源码
# 编译安装：perl Makefile.PL && make && make install
```

## 测试状态

| 功能 | 状态 |
|------|------|
| 模块加载 | ✅ PASS |
| HTTP GET | ✅ PASS (200 OK) |
| HTTPS | ⚠️ 未实现 |

## 注意事项

1. Clone 模块已用纯 Perl 版本替代
2. 使用时需确保所有依赖模块已安装
3. HTTPS 功能需额外安装 SSL 模块
4. 建议安装到系统 Perl 目录以避免 PERL5LIB 设置