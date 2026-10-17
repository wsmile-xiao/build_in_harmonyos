# uptimed

Uptime record daemon and top-uptime query tool — `uptimed` periodically
records boot events and uptime milestones, `uprecords` renders the
top-list of longest boot sessions.

- 上游仓库: https://github.com/rpodgorny/uptimed
- 版本: 0.4.6（上游 tag `v0.4.6`）
- 许可证: GPL-2.0-only（`COPYING`）
- 类型: 命令行工具（`bin/uptimed` 守护进程 + `bin/uprecords` 查询，R38 已附 `commands.json`）
- 构建系统: autotools（git-tag 归档无生成式 configure，需 autogen.sh 引导）

## 用途

- `uptimed`：记录每次开机（bootid）与累计运行时长里程碑，支持前台运行（`-f`）、
  采样间隔（`-i`）、记录上限（`-m`）、里程碑邮件通知（`-e`）等
- `uprecords`：按总时长/本次时长排序展示历史开机记录，支持 `-m` 条数、
  `-M` 下一个里程碑、`-w` 宽输出等

## OHOS 适配要点

- autogen.sh 引导 autotools；显式双 gnu 三元组使 `*-linux*` 分支生效（PLATFORM_LINUX，/proc/uptime）
- HMDFS umask 077 → mktemp wrapper + configure 内 022 放宽（E011/E114 受控方案）
- hnp bash getcwd 陷阱：unset CONFIG_SHELL + SHELL=/bin/sh（E386）
- 无 `make install`：纯 Python 拷贝 staging（dhcpoptinj/termrec 先例）
