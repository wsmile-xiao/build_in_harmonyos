# checkinstall

checkinstall 是一个"源码安装打包工具"：执行 `make install`（或任意安装命令）时，通过 **installwatch**（LD_PRELOAD 拦截库）跟踪所有写入文件，并生成 deb/rpm/slackware 原生安装包，实现"从源码安装的软件也能干净卸载"。

## 组成

| 组件 | 类型 | 说明 |
|------|------|------|
| `checkinstall` (sbin) | bash 脚本 | 主程序：打包 + 安装 |
| `makepak` (sbin) | bash 脚本 | 打包辅助脚本 |
| `installwatch` (bin) | bash 脚本 | LD_PRELOAD 包装器 |
| `installwatch.so` (lib) | C 库 | 拦截 make install 文件操作的拦截库 |

## HarmonyOS PC 适配

- **musl 移植**：installwatch.c 原深度绑定 glibc 版本化 stat ABI（`__xstat`/`_STAT_VER` 等），OHOS musl 无这些符号 → 补丁改为标准符号 interposer（`stat`/`lstat`/`mknod`/`fstatat`/`mknodat`），禁用 glibc 专属 64 位包装，构造函数改 `constructor/destructor`。
- **脚本 shebang**：`#!/bin/bash` → `#!/usr/bin/env bash`（OHOS 无 /bin/bash）。
- **libc 探针**：create-localdecls 依赖 gcc/ldd/glibc 头文件，OHOS 无 → 快速路径直接输出 musl 兼容值。
- **上游测试**：installwatch 自测核心拦截路径实测通过；chroot 项因 OHOS 沙盒禁止 chroot 系统调用（SIGSYS）无法运行，属平台限制。

## 上游

- 官方主页: https://checkinstall.izto.org/
- 官方仓库 gitlab.com/checkinstall/checkinstall 已 404，采用含完整官方历史的镜像仓库 github.com/giuliomoro/checkinstall @ d24a630（2017-04-26）
