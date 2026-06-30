# perl-net-pcap

Perl interface to the pcap (packet capture) library.

## 描述

Net::Pcap 是一个 Perl XS 模块，提供对 libpcap 库的 Perl 接口，用于网络数据包捕获和分析。它允许 Perl 程序执行数据包嗅探、网络流量分析和数据包过滤等操作。

## 版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.21-r2 | built | 2026-06-29 | OHOS 平台适配版，Conan 配方验证通过 |

## 依赖

- **libpcap** >= 1.8.0 (系统安装)
- **Perl** >= 5.10.0

## 构建

```bash
# 使用 Conan 构建
conan install --requires=perl-net-pcap/0.21-r2@ohpcd/stable
```

## OHOS 平台说明

- 编译使用 `perl Makefile.PL` 构建系统 (非 autotools)
- 补丁 `0001-Makefile.PL.patch` 跳过运行时库/函数检测 (HMDFS .so 加载限制)
- Pcap.so 需要 libpcap.so.1 运行时依赖
- XS .so 在 HMDFS 上受 SELinux 限制，需管理员安装到 `/data/service/hnp/`

## 许可证

MIT
