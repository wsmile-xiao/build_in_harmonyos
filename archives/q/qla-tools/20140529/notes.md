# qla-tools 20140529 适配笔记

## 编译环境
- 构建系统: 无（上游 `Architecture: all`，纯 shell 脚本包，无 configure/CMake/Makefile）
- 编译日期: 2026-09-29
- 目标平台: OHOS arm64（本机 HarmonyOS，`uname -r` = `HongMeng Kernel 1.12.0`）
- 状态: built（conan create + conan-verify 本地通过）

## 源码核验
- 上游源: `https://deb.debian.org/debian/pool/main/q/qla-tools/qla-tools_20140529.orig.tar.gz`
- sha256: `c3046cf8fea55b4cfd3884686b0f20503af007d7d40c1f238940af30e7c3a7d7`
  （与 Debian 官方 `.dsc` 的 `Checksums-Sha256` 一致，版本 20140529 核对无误）
- 上游组件: `ql-hba-snapshot/`、`ql-lun-state-online/`、`ql-set-cmd-timeout/`、
  `ql-dynamic-tgt-lun-disc/`（各含 `<name>.sh` + README + COPYING + revision）

## 编译步骤
无编译阶段。`conan create` 的 `source()` 下载解压源码，`build()` 仅应用 OHOS 补丁，
`package()` 将 4 个脚本按 Debian `usr/sbin/` 的命令名安装到 `bin/`：
`ql-xxx/ql-xxx.sh` → `bin/ql-xxx`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 直接执行脚本报 `bad interpreter: /bin/bash: no such file or directory`（exit 127）；改用 `#!/usr/bin/env bash` 后在 conan 测试环境仍报 `bad interpreter: Permission denied`（126） | OHOS 无 `/bin/bash`；且 `/usr/bin` 对部分运行 uid 不可遍历，`/usr/bin/env` 无法执行 | 4 个脚本 shebang 改 `#!/data/service/hnp/bin/bash`（OHOS 惯例，见 cryptsetup `ohos-bash-shebang`、dehydrated `rewrite-bin-sh-shebangs`） |
| 2 | `ql-hba-snapshot` 报 `[: too many arguments` | `uname -r` 返回 `HongMeng Kernel 1.12.0`（含空格，非 Linux 版本号），`[ $KERNEL_MAJ_MIN != 2.6 ]` 展开成多参数 | 内核门禁改 `case`：`2.6|3.*|4.*|5.*|6.*` 及 `*HongMeng*`/`*HarmonyOS*` 放行 |
| 3 | `ql-dynamic-tgt-lun-disc` 报 `mkdir: '/tmp/ql': Read-only file system` | OHOS `/tmp` 只读（E002）；脚本硬编码 `/tmp/ql/sg_utils`、`/tmp/ql-util` | 改 `${TMPDIR:-$HOME/tmp}/...`（`QL_TMPDIR`） |
| 4 | `ql-hba-snapshot` 使用只读 `/tmp/temp.scsi` | 同上 | `QL_TEMP="${TMPDIR:-$HOME/tmp}/temp.scsi"` |
| 5 | 多脚本输出 `tput: command not found` | OHOS 无 `tput`（ncurses-utils） | `echo_b()` 中改 `command -v tput >/dev/null 2>&1 && tput sgr0` |
| 6 | `ql-dynamic-tgt-lun-disc` 走 sg 模块加载分支时 `modprobe: command not found` | OHOS 无 `modprobe`（kmod） | 改 `command -v modprobe >/dev/null 2>&1 && modprobe sg` |

> 问题 1 为「首个真实错误」（exit 127），问题 2/3 为使用 `bash` 显式执行后暴露的
> OHOS 平台问题。修改均为最小必要改动，未触碰脚本主逻辑与硬件交互路径。

## 源码修改（patches/）
- `0001-ql-dynamic-tgt-lun-disc-ql-dynamic-tgt-lun-disc.sh.patch`
- `0002-ql-hba-snapshot-ql-hba-snapshot.sh.patch`
- `0003-ql-lun-state-online-ql-lun-state-online.sh.patch`
- `0004-ql-set-cmd-timeout-ql-set-cmd-timeout.sh.patch`

修改点：shebang（4 脚本，改 `/data/service/hnp/bin/bash`）、内核门禁（2 脚本）、临时目录（2 脚本）、tput（4 脚本）、
modprobe（1 脚本）。补丁内**未使用** `__OHOS__` 平台宏（R8）。

## 依赖版本
- 强制第三方依赖: `libsgutils/1.46`（上游 `Depends: sg3-utils`；提供 `sg_turs`/`sg_map`）
  - 已发布可消费: `conan download libsgutils/1.46 -r=ohpcd --only-recipe` → EXIT=0

## 上游测试清点（R51）
- 源码树无 `tests/`/`test/`，无任何 `*test*` 文件
- Debian 打包层无 `debian/tests/`
- `debian/rules` 无 `dh_auto_test` / `make check`
- **结论：上游无自动化测试入口**（仅有 4 个脚本的使用说明 README）

## 验证结果

```bash
# 适配前后对比（本机 OHOS）
$ ./ql-hba-snapshot/ql-hba-snapshot.sh --help        # 适配前
bad interpreter: /bin/bash: no such file or directory ; EXIT=127

$ bash -n <4 个脚本>                                  # 语法检查
OK ×4

$ ./<script> -h                                       # 适配后 shebang 直接执行
ql-hba-snapshot        EXIT=1  stderr 空（走 module 门禁）
ql-lun-state-online    EXIT=0  stderr 空
ql-set-cmd-timeout     EXIT=0  stderr 空
ql-dynamic-tgt-lun-disc EXIT=1 stderr 空

$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
...
qla-tools/20140529 (test package): RUN: /data/service/hnp/bin/bash test.sh
qla-tools 20140529 test_package: TOTAL=8 PASS=8 FAIL=0 SKIP=0
```

## 注意事项
- 工具的完整功能依赖 QLogic `qla2xxx`/`qla4xxx` 驱动与真实 FC/iSCSI HBA（sysfs
  `/sys/class/scsi_host`、`/sys/bus/pci/drivers/qla*`）。无 HBA 时按设计打印
  “no host”信息并退出，属预期行为，非适配缺陷。
---

**编译结束**: 2026-09-29 21:16
**最终状态**: built
