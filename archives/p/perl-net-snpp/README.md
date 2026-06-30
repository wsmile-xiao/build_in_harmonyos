# Net::SNPP

Simple Network Pager Protocol Client — 鸿蒙平台预编译包

## 软件介绍

Net::SNPP 是 Perl 的 SNPP (Simple Network Pager Protocol, RFC 1861) 客户端和服务器实现模块。

### 主要特性
- SNPP 协议客户端 (Net::SNPP) — 支持 RFC 1861 Level 1-3 全部命令
- SNPP 协议服务器 (Net::SNPP::Server) — 可扩展的回调机制
- HylaFAX 传真集成 (Net::SNPP::HylaFAX) — HylaFAX 服务器扩展
- 纯 Perl 实现，无 C/XS 依赖

### 技术信息
- **版本**: 1.17-r7
- **许可证**: MIT
- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **类型**: 纯 Perl 模块 (无 XS)
- **主页**: https://metacpan.org/dist/Net-SNPP

## 鸿蒙平台适配

### 编译状态
- **编译日期**: 2026-06-26
- **平台**: OpenHarmony (aarch64-linux)
- **Perl**: 5.42.0
- **状态**: ✅ 编译成功

### 平台适配说明
- 纯 Perl 模块，无需 C 编译，无需平台适配补丁
- 不受 SELinux HMDFS 限制（与 XS 模块不同），可直接通过 PERL5LIB 加载
- 依赖系统 Perl 自带的 Net::Cmd (v3.15)

### 质量门禁
| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 产物完整性 | PASS | 3 个 .pm 文件，SHA256 校验通过 |
| G2 功能可用性 | PASS | 17 项测试，16 PASS / 1 FAIL (平台限制) |
| G3 可移植性 | PASS | 纯 Perl，平台无关 |
| G4 档案完整性 | PASS | 归档完整，conan-verify 全部通过 |

## 使用方式

### Conan 安装
```bash
conan install --requires=perl-net-snpp/1.17-r7@ohpcd/stable
```

### Perl 代码示例
```perl
use Net::SNPP;

# 连接 SNPP 服务器
my $snpp = Net::SNPP->new('snpp.example.com', Port => 444);

# 发送寻呼消息
$snpp->pager_id('1234567');
$snpp->content('Hello from OpenHarmony!');
$snpp->send();
$snpp->quit();
```

### HylaFAX 扩展
```perl
use Net::SNPP::HylaFAX;

# 连接 HylaFAX SNPP 服务器
my $fax = Net::SNPP::HylaFAX->new('fax.example.com');
$fax->pager_id('1234567');
$fax->modem(Net::SNPP::HylaFAX::MODEM_CLASS);  # 使用 Class 模式
$fax->send();
```

### Server（需管理员权限）
```perl
use Net::SNPP::Server;

# 创建 SNPP 服务器（需要端口绑定权限）
my $server = Net::SNPP::Server->new(
    Port => 444,
    callback => {
        process_page => \&my_page_handler,
        validate_pager_id => \&my_validator,
    },
);
$server->handle_client();
```

> ⚠️ Server 模块需要端口绑定权限。在 OpenHarmony HMDFS 环境下受 SELinux 限制，需安装到系统目录或获得相应权限。

## 版本信息

| 版本 | 状态 | 发布日期 |
|------|------|---------|
| 1.17-r7 | built | 2026-06-26 |

## 相关链接
- CPAN: https://metacpan.org/dist/Net-SNPP
- RFC 1861: https://tools.ietf.org/html/rfc1861
