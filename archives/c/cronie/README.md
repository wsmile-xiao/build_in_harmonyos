# Cronie

Cronie is a cron daemon for Linux that includes standard cron features with anacron (a cron clone that runs jobs that were missed due to system downtime) extensions.

## 功能概述

- **标准 cron 功能**：定时任务调度
- **anacron 扩展**：支持系统关机期间错过的任务
- **crontab 管理**：用户级别的任务配置
- **cronnext 工具**：查看下次执行时间

## OHOS 适配要点

### HMDFS 临时文件限制

在 OHOS 的 HMDFS 文件系统上，autotools 的 config.status 无法在当前目录创建临时文件（mktemp 创建的目录权限过于严格，且 chmod 不生效）。解决方案：

1. 修改 config.status 脚本，使用预先创建的固定临时目录
2. 确保临时目录权限为 1777（drwxrwsrwx）

### automake 版本

automake 1.17 的 Perl 模块与 OHOS 的 Perl 不兼容，建议安装 automake 1.16.5：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- automake 1.16.5
```

### configure 脚本生成

从 Gitee/GitHub 下载的源码包可能不包含 configure 脚本，需要手动生成：

```bash
aclocal-1.16 && autoconf && autoheader && automake-1.16 --add-missing
```

## 依赖关系

编译依赖：
- autoconf
- automake 1.16.x
- clang
- make

运行依赖：
- 无特殊依赖（cronie 是独立的 daemon）

## 编译产物

- `bin/cronnext` - 下次执行时间查询工具
- `bin/crontab` - 用户任务配置工具
- `sbin/crond` - cron daemon
- `sbin/anacron` - anacron daemon

## 参考资料

- 官方仓库：https://github.com/cronie-crond/cronie
- Gitee 镜像：https://gitee.com/mirrors/cronie