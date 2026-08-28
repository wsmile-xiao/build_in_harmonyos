# backuppc-rsync 3.1.3.0 for HarmonyOS

## 概述

backuppc-rsync（上游名 rsync-bpc）是 BackupPC 备份系统定制的 rsync：在
rsync 3.1.3 基础上增加 BackupPC 池文件系统 shim 层，使 rsync 可直接读写
BackupPC 池格式。产物为单一命令行工具 `rsync_bpc`，与原生 rsync 协议线级
兼容，也可作为普通 rsync 使用。

| 项目 | 值 |
|------|-----|
| 名称 | backuppc-rsync (rsync-bpc) |
| 版本 | 3.1.3.0 |
| 上游仓库 | https://github.com/backuppc/rsync-bpc |
| 源码包 | https://github.com/backuppc/rsync-bpc/releases/download/3.1.3.0/rsync-bpc-3.1.3.0.tar.gz |
| 许可证 | GPL-3.0 |
| 构建系统 | autotools（configure 包装器 + configure.sh） |
| 产物 | bin/rsync_bpc |

## 鸿蒙适配要点

| 问题 | 解决 | 知识条目 |
|------|------|---------|
| config.guess(2013)/config.sub(2013) 不识别 HarmonyOS | 补丁替换为带 OHOS 支持的版本；旧式脚本用 echo+exit 语法 | E007 |
| config.status mktemp 在 HMDFS 权限不足 | build() 中程序化重定向到 $TMPDIR | E114 |
| 脚本 shebang /bin/sh 不存在 | OHOS 下改写为 /system/bin/sh | E165 |
| getpass 有符号无头文件声明 | config.h 中 undef HAVE_GETPASS | — |
| OHOS 无 libpopt | --with-included-popt 使用源码内置 popt | — |
| FALLOC_FL_ZERO_RANGE 编译报 undeclared identifier | syscall.c 条件包含 <linux/falloc.h>，使用点同时校验宏可见性，缺失时走写零回退 | — |

依赖说明：zlib 为 rsync 3.1.x 内置实现、popt 内置，包无外部 Conan 依赖。
按 R26 以 `-static` 静态链接。

## 上游测试

上游发布包不含测试套件（testsuite 被 BackupPC 打包移除，Makefile.in 无
check 目标），显式审计见 `3.1.3.0/test_package/MANIFEST.yml`。
test_package 提供 8 项内容级功能用例真实执行 bin/rsync_bpc：
--version、单文件同步、递归目录树同步、更新传播、校验和模式(-rc)、
--delete 删除传播、--dry-run、--exclude 过滤。

## 验证

在 HarmonyOS aarch64 环境实测（以 CI 最终结果为准）：

```bash
# 版本验证
rsync_bpc --version
# rsync  version 3.1.3.0  protocol version 29 ...

# 本地同步
mkdir -p $TMPDIR/src $TMPDIR/dst
echo "hello" > $TMPDIR/src/hello.txt
rsync_bpc -r $TMPDIR/src/ $TMPDIR/dst/
cat $TMPDIR/dst/hello.txt
```

## 参考资料

- https://github.com/backuppc/rsync-bpc
- BackupPC 项目主页 https://github.com/backuppc/backuppc
