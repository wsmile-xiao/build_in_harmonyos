# Net::IP

Perl 模块，提供 IPv4/IPv6 地址操作功能，包括地址解析、验证、压缩/展开、子网计算、范围遍历等。

## 主要功能

- `ip_is_ipv4($ip)` / `ip_is_ipv6($ip)` — IPv4/IPv6 地址验证
- `ip_get_version($ip)` — 自动检测 IP 版本
- `ip_compress_address($ip, $ver)` — IPv6 地址压缩
- `ip_expand_address($ip, $ver)` — IPv6 地址展开
- `ip_iptobin($ip, $ver)` / `ip_bintoip($bin, $ver)` — IP 与二进制互转
- `Net::IP->new($cidr)` — 对象接口，支持 prefix/mask/binmask/last_ip/intip 等
- `ipcount` — 命令行工具，计算 CIDR 范围内的 IP 数量
- `iptab` — 命令行工具，显示 CIDR 前缀对照表

## 编译指导

纯 Perl 模块，使用 Makefile.PL 构建，无需 C 编译器：

```bash
perl Makefile.PL
make
make test  # 36069 个测试
make install DESTDIR=/tmp/destdir
# 复制 .pm 和脚本到标准位置
cp /tmp/destdir/.../Net/IP.pm lib/perl5/Net/IP.pm
cp /tmp/destdir/.../bin/ipcount bin/
cp /tmp/destdir/.../bin/iptab bin/
```

### HarmonyOS 注意事项

- 纯 Perl 模块，不受 SELinux/HMDFS 限制，可直接安装使用
- 无外部依赖，仅需 Perl 5.42.0
- conan-verify G4 检查存在已知限制：`conan cache path` 返回 export 目录而非包二进制目录，需手动验证产物完整性

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.26-r7](./1.26-r7/) | published | 2026-06-26 |
