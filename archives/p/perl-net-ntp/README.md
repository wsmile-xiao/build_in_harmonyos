# perl-net-ntp

Perl extension for decoding NTP server responses (Net::NTP).

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.5-r1 | published | 2026-06-26 | OHOS 平台适配，修复 getservbyname 段错误 |

## 使用说明

```perl
use Net::NTP qw(get_ntp_response);

# 查询 NTP 服务器（OHOS 平台需传入数字端口或使用补丁修复后的版本）
my %response = get_ntp_response("pool.ntp.org");
print "Stratum: $response{Stratum}\n";
print "Offset: $response{Offset}\n";
```

## 依赖

- Perl 5.8+（纯 Perl 模块，无 C/XS 编译）
- Time::HiRes（Perl 核心模块）
- IO::Socket（Perl 核心模块）
