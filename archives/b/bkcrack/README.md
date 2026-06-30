# bkcrack

> 使用 Biham 和 Kocher 的已知明文攻击破解传统 ZIP 加密。

bkcrack 是一个实现 Biham 和 Kocher 对 ZipCrypto（ZIP 归档使用的传统加密方案）已知明文攻击的工具。它可以从已知明文中恢复内部加密密钥，并使用这些密钥解密归档其余部分、恢复原始密码或更改密码。

## 可用版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.8.1 | ✅ 已发布 (published) | 2026-06-03 |

## 构建系统

- cmake（需要 C++17 编译器支持）

## 许可证

- Zlib 许可证（见源码 license.txt）

## 外部依赖

- 无（纯 C++ 工具，仅依赖系统 pthread）

## 源码地址

- https://github.com/kimci86/bkcrack

## 主要功能

- 已知明文攻击破解传统 ZipCrypto 加密
- 暴力破解和掩码搜索恢复密码
- 不需要密码即可解密数据
- 使用恢复的密钥更改归档密码
- 列出 ZIP 归档条目

## 用法

```bash
bkcrack --version    # 查看版本
bkcrack --help       # 查看帮助
bkcrack -C secrets.zip -c spiral.svg ... # 执行已知明文攻击
```

## HarmonyOS 适配说明

- 需要安装路径补丁（原始 DESTINATION . 改为 bin/ 和 share/bkcrack/）
- cmake 会报 "System is unknown" 警告，但不影响编译和运行
- 31个功能测试全部通过