# snapraid

**基于奇偶校验的磁盘阵列快照备份工具**（备份程序，来自 SnapRAID 项目）

SnapRAID 面向家庭/小型磁盘阵列：为磁盘阵列计算并维护奇偶校验数据（支持 1~6 重校验，对应最多六块数据盘同时故障的恢复能力），数据盘只读入不改动；损坏时用校验数据恢复。适合存储大量不常变动数据（媒体库、归档等）的增量备份场景。

## 用法

```bash
snapraid sync     # 数据变化后更新校验
snapraid scrub    # 周期性校验，及早发现静默损坏
snapraid check    # 全量校验
snapraid fix      # 修复损坏的文件
snapraid status   # 阵列状态
```

配置文件（默认 `/etc/snapraid.conf`）声明 parity/content/disk 各项；详见上游文档 https://www.snapraid.it/。

## 归档信息

- 上游：https://github.com/amadvance/snapraid （GPL-3.0-or-later，C + autotools）
- 本归档版本：14.9（分支 `feat/snapraid-14.9`）
- 构建系统：autotools（tarball 自带 configure）
- 平台适配：OHOS aarch64（HMDFS 文件系统适配见版本目录 notes.md：E007/E011/E114/E079 知识应用 + 上游测试套件平台旗标）
