# ccrypt

## 软件简介
ccrypt 是一个安全的文件加密和解密工具，基于 Rijndael 算法（AES）。

## 功能特性
- 文件加密/解密
- 流加密
- 密钥猜测工具 (ccguess)
- 支持标准 Unix crypt 兼容模式

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.11 | built | 2026-06-06 | 首次鸿蒙适配编译 |

## 使用方法

### 加密文件
```bash
ccrypt -e filename
# 或使用密钥文件
ccrypt -k keyfile -e filename
```

### 解密文件
```bash
ccrypt -d filename.cpt
# 或使用密钥文件
ccrypt -k keyfile -d filename.cpt
```

### 相关命令
- `ccencrypt`: 加密文件（ccrypt 符号链接）
- `ccdecrypt`: 解密文件（ccrypt 符号链接）
- `ccat`: 解密并查看文件（ccrypt 符号链接）
- `ccguess`: 密钥猜测工具

## 鸿蒙平台适配说明

### 平台限制
- 测试脚本 `/tmp` 只读问题已记录
- 核心加密功能正常可用

### 依赖
- libcrypt (系统库)

## 许可证
GPL-2.0-or-later

## 官方网站
https://ccrypt.sourceforge.net/