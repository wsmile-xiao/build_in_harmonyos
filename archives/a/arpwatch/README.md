# arpwatch

## 简介
arpwatch是一个网络监控工具，用于跟踪以太网/IP地址配对，并通过电子邮件报告特定变更。

## 功能特性
- 监控以太网和FDDI活动
- 维护以太网/IP地址配对数据库
- 检测并报告MAC地址变更
- 支持SNMP数据收集（arpsnmp）
- 自动更新以太网供应商代码

## 依赖
- libpcap (必需)
- Net-SNMP (可选，用于arpsnmp)

## 编译选项
- `--prefix=$DEFAULT_PREFIX`: 标准安装前缀

## 版本历史
- 3.9 (2025-10-24): 当前版本

## 参考资料
- 官方网站: https://ee.lbl.gov/downloads/arpwatch/
- 源码: https://ee.lbl.gov/downloads/arpwatch/arpwatch-3.9.tar.gz
