# libmcrypt

加密算法库，提供多种对称加密算法的实现。

## 功能概述

- 提供 DES, 3DES, Blowfish, AES 等加密算法
- 支持流加密和块加密模式
- 提供命令行加密工具

## OHOS 适配要点

1. **老版本 autotools 处理**：
   - config.guess 是 2003 年老版本，使用 GUESS 变量格式
   - 需改为直接 echo/exit 格式以支持 HarmonyOS
2. **平台识别**：
   - config.sub 需添加 `linux-ohos*` triplet
3. **HMDFS 权限**：
   - configure 中 `umask 077` 需改为 `umask 022`
   - config.guess 中同样需要修改

## 依赖关系

- 无外部依赖

## 编译步骤

```bash
sed -i 's/umask 077/umask 022/g' configure config.guess
# 应用 config.guess/config.sub 补丁
./configure --prefix=$DEFAULT_PREFIX
make -j$(nproc)
make check
make install
```

## 补丁说明

- 0001: config.guess HarmonyOS 识别（老版本格式）
- 0002: config.sub triplet 支持
- 0003: configure umask 修复

## 参考资料

- 官网：https://mcrypt.sourceforge.net