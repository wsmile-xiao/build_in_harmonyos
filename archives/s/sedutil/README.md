# sedutil

自加密硬盘（SED）管理工具，支持 Trusted Computing Group (TCG) OPAL 2.0 SSC 规范。

## 功能

- 扫描系统中符合 OPAL 规范的磁盘
- 查询磁盘 Discovery 0 响应
- 管理锁定范围（Locking Range）：启用/禁用、锁定/解锁、加密/解密
- 管理 Admin1/User 密码、PSID 重置
- PBKDF2 密码哈希验证

## 上游信息

- 上游地址: https://github.com/Drive-Trust-Alliance/sedutil
- 版本: 1.20.0
- 许可证: GPL-3.0
- 构建系统: autotools (configure.ac + Makefile.am)

## 产物

- `sedutil-cli` — 主命令行工具（安装到 sbin）
- `sedutil-pba` — 预启动认证程序（原 linuxpba，因 OHOS HMDFS 大小写不敏感文件系统与 LinuxPBA 源码目录路径冲突而改名）

## 适配说明

- OHOS 无 `/bin/bash`：GitVersion.sh shebang 改为 `/bin/sh`
- OHOS sysroot 提供 `linux/nvme_ioctl.h`（内核 5.10 >= 4.4）：DtaDevLinuxNvme.h 直接包含 nvme_ioctl.h，去掉 version.h 版本判断与旧 nvme.h 路径
- 系统 `usr/local/include/sha1.h` 遮蔽项目内 cifra 的 sha1.h：DtaHashPwd.cpp 改为相对路径包含 `pbkdf2/sha1.h`
- 无第三方库依赖
