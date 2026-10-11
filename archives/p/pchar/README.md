# pchar — Path Char（网络路径特征分析）

## 软件简介

pchar（"Path Char"）是 Sandia National Laboratories 出品的网络路径特征分析工具。
它向目标主机发送 ICMP、UDP 或 TCP 探测包，并对往返时延（RTT）、抖动（jitter）、
丢包率进行统计，同时输出路径斜率/截距回归分析结果。

**主要功能**:
- ICMP / UDP / TCP 多种探测类型（`-t` 选择），支持 IPv6
- RTT 最小/最大/平均/标准差、抖动统计
- 路径斜率/截距回归分析（result table）
- 统计结果可写入文件（`-w`）

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 1.5 | built ✅ | 2026-10-11 | 7 |

## 使用方法

```bash
# 探测目标主机（ICMP 探测需要足够权限，普通用户可用 -t 2 选 UDP）
pchar 192.168.1.1

# 查看版本 / 帮助
pchar -V
pchar -h
```

## 许可证

美国联邦政府作品（Sandia/DOE 声明：将权利奉献给公众，as-is 提供，无担保）。
