# cryptmount

加密文件系统管理工具，用于管理 Linux device-mapper 加密设备。

## 描述

cryptmount 是一个用于管理和挂载加密文件系统的工具，它使用 Linux device-mapper 框架来创建和管理加密设备。

## 版本

- 6.4.0 (最新)

## 依赖

- libdevmapper (device-mapper 用户空间库)
- libintl (国际化库)

## HarmonyOS 注意事项

1. 需要先编译 LVM2 获取 libdevmapper
2. 鸿蒙缺少 mntent 函数，需要 stub 实现
3. 加密功能可能受限（缺少 libgcrypt/LUKS支持）

## 安装

```bash
# 使用预编译包安装
curl -fsSL install.sh | sh -s -- cryptmount 6.4.0
```

## 参考

- 官方主页：https://www.nongnu.org/cryptmount/
- Debian 源码：https://deb.debian.org/debian/pool/main/c/cryptmount/