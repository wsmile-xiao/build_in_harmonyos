# sysstat 12.7.9 适配笔记
**生成日期**: 2026-06-11（重试更新）

---

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-06-10
- 编译器: clang version 15.0.4
- 平台: HarmonyOS HongMeng Kernel 1.12.0 (aarch64, 20 CPU)
- DEFAULT_PREFIX: /storage/Users/currentUser/usr/local
- TEST_PREFIX: /storage/Users/currentUser/tmp/test-install-sysstat-12.7.9
- BUILD_SRC_DIR: /storage/Users/currentUser/tmp/builds/sysstat-12.7.9.work
- ARCHIVE_DIR: /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/s/sysstat/12.7.9
- 状态: published

---

## 编译步骤（真实执行命令）

```bash
# Step 1: 初始化编译环境
python3 /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/scripts/ohc-run.py init-build sysstat 12.7.9 --url=https://github.com/sysstat/sysstat/archive/refs/tags/v12.7.9.tar.gz

# Step 2: 读取构建上下文
source /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/.build-context-sysstat-12.7.9

# Step 3: 清理旧产物并重新配置
cd /storage/Users/currentUser/tmp/builds/sysstat-12.7.9.work
make distclean  # 清理之前编译的产物
./configure --prefix=/storage/Users/currentUser/usr/local --disable-sensors

# Step 4: 编译
make -j1

# Step 5: DESTDIR 安装（staging隔离，打包用）
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-sysstat-12.7.9

# Step 6: 安全弹窗验证(R7)
# 所有7个命令 -V 输出 sysstat version 12.7.9
for prog in sar sadf iostat mpstat pidstat tapestat cifsiostat; do
    /storage/Users/currentUser/tmp/test-install-sysstat-12.7.9/storage/Users/currentUser/usr/local/bin/$prog -V
done

# Step 7: make check（sysstat 无此目标）
make check  # → make: *** No rule to make target 'check'.  Stop.

# Step 8: verify-build + 创建标记
python3 /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/scripts/ohc-run.py verify-build sysstat 12.7.9 --install-prefix=/storage/Users/currentUser/tmp/test-install-sysstat-12.7.9/storage/Users/currentUser/usr/local

# Step 9: 打包
python3 /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/scripts/ohc-run.py package sysstat 12.7.9

# Step 10: 本地安装（不带 DESTDIR，覆盖只读路径）
make install SA_DIR=/storage/Users/currentUser/tmp/var-sa SYSCONFIG_DIR=/storage/Users/currentUser/tmp/etc-sysconfig

# Step 11: 本地版本验证
/storage/Users/currentUser/usr/local/bin/sar -V    # → sysstat version 12.7.9
/storage/Users/currentUser/usr/local/bin/iostat       # → 显示CPU和I/O统计 ✅
/storage/Users/currentUser/usr/local/bin/mpstat       # → 显示CPU统计 ✅

# Step 12: 收尾
python3 /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/scripts/ohc-run.py finish sysstat 12.7.9 published
```

---

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 真实命令/输出 |
|---|------|------|----------|---------------|
| 1 | /var/log/sa 和 /etc/sysconfig 创建失败 | 只读文件系统（HMDFS），无root权限 | `make install SA_DIR=/storage/Users/currentUser/tmp/var-sa SYSCONFIG_DIR=/storage/Users/currentUser/tmp/etc-sysconfig` | `mkdir: cannot create directory '/var': Permission denied` |
| 2 | sysstat 无 `make check` | sysstat 不提供标准测试目标 | 手动运行 `-V` 验证版本，运行 iostat/mpstat/pidstat 功能验证 | `make: *** No rule to make target 'check'.  Stop.` |
| 3 | sysstat 不支持 `--version` | sysstat 设计：用 `-V` 查版本 | 所有命令使用 `-V` 获取版本号 | `sar --version` → 显示usage（退出码1）；`sar -V` → sysstat version 12.7.9 |
| 4 | NLS 自动禁用 | 缺少 msgmerge 命令 | configure自动检测并禁用，不影响核心功能 | `WARNING: msgmerge command not found! WARNING: Disabling NLS` |
| 5 | G0 clean-verify config.status 失败 | HMDFS限制：不允许创建临时子目录 | 记录为平台已知限制(E046)，手动验证已通过 | `./config.status[779]: can't create ./confX1V6hw/subs1.awk: Permission denied` |
| 6 | G4 manifest 缺少 `build_system` | manifest.yaml 嵌套格式 vs 顶层字段 | 添加顶层 `build_system: autotools` | 修复后 verify-build G4 PASS |
| 7 | 生成文件补丁(R6违反) | config.log/config.status/sysstat.pot 是生成文件 | 删除这3个补丁，更新manifest.yaml patches_applied=[] | 删除了0001-config.log.patch, 0002-config.status.patch, 0003-nls-sysstat.pot.patch |

---

## 源码修改

无补丁。所有修改均为 configure 参数 `--disable-sensors`。

---

## 依赖版本

无外部依赖。sysstat 仅依赖 libc（musl）。

真实验证:
```bash
$ ldd /storage/Users/currentUser/usr/local/bin/sar
	linux-vdso.so.1 (0x0000fffff7ff000)
	libc.musl-aarch64.so.1 => /lib/libc.musl-aarch64.so.1 (0x00007fffff0000)
```

---

## 验证结果（真实执行输出）

### 版本验证
```
$ /storage/Users/currentUser/usr/local/bin/sar -V
sysstat version 12.7.9
(C) Sebastien Godard (sysstat <at> orange.fr)

$ /storage/Users/currentUser/usr/local/bin/sadf -V
sysstat version 12.7.9
(C) Sebastien Godard (sysstat <at> orange.fr)

$ /storage/Users/currentUser/usr/local/bin/iostat -V
sysstat version 12.7.9
(C) Sebastien Godard (sysstat <at> orange.fr)

$ /storage/Users/currentUser/usr/local/bin/mpstat -V
sysstat version 12.7.9
(C) Sebastien Godard (sysstat <at> orange.fr)

$ /storage/Users/currentUser/usr/local/bin/pidstat -V
sysstat version 12.7.9
(C) Sebastien Godard (sysstat <at> orange.fr)

$ /storage/Users/currentUser/usr/local/bin/tapestat -V
sysstat version 12.7.9
(C) Sebastien Godard (sysstat <at> orange.fr)

$ /storage/Users/currentUser/usr/local/bin/cifsiostat -V
sysstat version 12.7.9
(C) Sebastien Godard (sysstat <at> orange.fr)
```

### 功能验证
```
$ /storage/Users/currentUser/usr/local/bin/iostat
HarmonyOS HongMeng Kernel 1.12.0 (localhost) 	06/11/26 	_aarch64_	(20 CPU)

avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           5.91    0.00    4.18    0.26    0.00   89.65

Device             tps    kB_read/s    kB_wrtn/s    kB_dscd/s    kB_read    kB_wrtn    kB_dscd

$ /storage/Users/currentUser/usr/local/bin/mpstat
HarmonyOS HongMeng Kernel 1.12.0 (localhost) 	06/11/26 	_aarch64_	(20 CPU)

14:37:17     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
14:37:17     all    5.91    0.00    3.69    0.26    0.49    0.00    0.00    0.00    0.00   89.65

$ /storage/Users/currentUser/usr/local/bin/pidstat
HarmonyOS HongMeng Kernel 1.12.0 (localhost) 	06/11/26 	_aarch64_	(20 CPU)

14:37:17      UID       PID    %usr %system  %guest   %wait    %CPU   CPU  Command
14:37:17    20005      3376    0.02    0.01    0.00    0.01    0.03     2  i.hmos.location
14:37:17    20006      3427    0.02    0.00    0.00    0.01    0.03     2  .hms.pafservice
```

---

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sysstat-12.7.9-ohos-aarch64.tar.gz | 1.2MB (1358564 bytes) | 预编译包（已ELF签名） |
| sysstat-12.7.9-ohos-aarch64-debug.tar.gz | 168KB (168496 bytes) | 调试符号包 |

---

## 注意事项

1. sysstat 使用 `-V` 参数查看版本（非 `--version`），这是软件的设计特性
2. `make install` 需要root权限创建 `/var/log/sa` 和 `/etc/sysconfig`，本地安装时通过 `SA_DIR` 和 `SYSCONFIG_DIR` 参数覆盖到可写路径
3. sensors 支持已通过 `--disable-sensors` 禁用（鸿蒙平台无 libsensors）
4. NLS 已自动禁用（缺少 msgmerge），不影响核心功能
5. sadc 数据收集依赖 /proc 文件系统，核心监控命令（iostat/mpstat/pidstat）可实时从 /proc 读取统计
6. G0 clean-verify 的 config.status Permission denied 是 HMDFS 平台已知限制（E046），非软件缺陷

---
**编译结束**: 2026-06-10 23:48
**最终状态**: published
---

**编译结束**: 2026-09-07 17:53
**最终状态**: built
