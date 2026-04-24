# RHash 编译档案

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | RHash |
| 官网 | http://rhash.sourceforge.net/ |
| GitHub | https://github.com/rhash/RHash |
| 描述 | 递归哈希计算工具，支持多种哈希算法 |

## 已编译版本

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 1.4.4 | ✅ success | 2026-04-24 | 静态编译，禁用 gettext |

## 功能特性

- 递归处理目录
- 支持 CRC32, CRC32C, MD4, MD5, SHA1, SHA256, SHA512, SHA3
- 支持 AICH, ED2K, TTH, BTIH, Tiger
- 支持 GOST, RIPEMD-160, HAS-160, EDON-R, Whirlpool, Blake2
- 输出 SFV/BSD 格式或用户自定义格式
- 计算 Magnet 链接

## 鸿蒙适配说明

- 使用静态编译模式以避免 HMDFS 软链接限制
- 禁用 gettext 国际化支持（编译兼容性问题）
- 所有测试 24/24 通过

## 安装方式

```bash
# 下载预编译包
tar -xzf rhash-1.4.4-ohos-aarch64.tar.gz
cd rhash-1.4.4-ohos-aarch64
./install-rhash-1.4.4.sh

# 验证
rhash --version
```

## 参考链接

- [RHash 官方网站](http://rhash.sourceforge.net/)
- [RHash GitHub](https://github.com/rhash/RHash)
- [LibRHash 文档](https://github.com/rhash/RHash/blob/master/docs/LIBRHASH.md)