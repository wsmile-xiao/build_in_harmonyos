# qla-tools

QLogic 提供的 Linux FC/iSCSI HBA 管理脚本集，用于简化 QLogic HBA 的 LUN 增删与
日常运维。Debian 源码包，`Architecture: all`，纯 shell 脚本、无编译阶段。

## 包含命令

| 命令 | 说明 |
|------|------|
| `ql-hba-snapshot` | 显示 QLogic HBA / target / LUN 详细信息（sysfs 或 procfs） |
| `ql-lun-state-online` | 将 offline 的 LUN 恢复为 online/running |
| `ql-set-cmd-timeout` | 查看 / 修改设备命令超时 |
| `ql-dynamic-tgt-lun-disc` | 动态发现 / 重扫 target LUN（`-r` 可移除已消失的 LUN） |

## 上游信息

- 上游：QLogic Linux tools for QLogic HBAs（<http://driverdownloads.qlogic.com>）
- 源码：Debian 源码包 `qla-tools`，版本号即脚本快照日期 `20140529`
- 源码快照：`qla-tools_20140529.orig.tar.gz`（Debian 官方源码池，sha256 与 .dsc 一致）
- 许可：GPL-2.0-or-later

## OHOS 适配要点

1. **shebang**：OHOS 无 `/bin/bash`，且 `/usr/bin` 对部分运行 uid 不可遍历（`/usr/bin/env` 无法执行），
   4 个脚本 shebang 统一改为 `#!/data/service/hnp/bin/bash`（OHOS 惯例）。
2. **临时文件**：OHOS `/tmp` 只读（E002），硬编码的 `/tmp/...` 改为
   `${TMPDIR:-$HOME/tmp}/...`。
3. **内核门禁**：`uname -r` 在 OHOS 返回 `HongMeng Kernel 1.12.0`（非 Linux 版本号），
   原 2.6 门禁会误判；改为 case 匹配 `2.6|3.*|4.*|5.*|6.*` 及 `*HongMeng*`/`*HarmonyOS*`。
4. **缺失工具降级**：`tput`（ncurses-utils）、`modprobe`（kmod）在 OHOS 上缺失，
   调用前用 `command -v` 判空降级，避免噪声报错。

## 运行时依赖

- `libsgutils/1.46`（上游 `Depends: sg3-utils`）—— `ql-dynamic-tgt-lun-disc` 使用
  `sg_turs` / `sg_map`。

## 测试

上游无自动化测试套件。适配后消费者测试 `test_package/test.sh` 共 8 个用例
（含 3 个鸿蒙特有：shebang 解析、只读 /tmp、HarmonyOS 内核串放行）。
