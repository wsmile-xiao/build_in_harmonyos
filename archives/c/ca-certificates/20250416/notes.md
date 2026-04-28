# ca-certificates 20250416 适配笔记

## 编译环境
- 构建系统: custom（纯数据包）
- 编译日期: 2026-04-27
- 编译器: N/A
- 状态: partial

## 编译步骤
ca-certificates 是纯数据包，不需要编译。证书文件需要从 Mozilla certdata.txt 生成。

由于缺少 Python cryptography 模块，无法运行 certdata2pem.py，因此从 Debian 预编译包提取了证书文件。

手动安装：
1. 创建目标目录 `share/ca-certificates/mozilla/`
2. 复制 150 个 Mozilla CA 证书文件
3. 复制 update-ca-certificates 工具和手册页

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | certdata2pem.py 无法运行 | 缺少 Python cryptography 模块 | 从 Debian 预编译包提取证书 |

## 依赖版本
无依赖

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| ca-certificates-20250416-ohos-aarch64.tar.gz | 339.1KB | 主包 |
