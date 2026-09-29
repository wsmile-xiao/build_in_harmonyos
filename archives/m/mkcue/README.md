# mkcue

从 CD 的 TOC（Table Of Contents）生成 CUE sheet 的命令行工具。

- 上游：Eric Gillespie（`epg@pretzelnet.org`），分发点 <https://diplodocus.org/>
  - 上游只有 **Subversion** 仓库（`svn+ssh://diplodocus.org/svn/projects/release/mkcue-1/`），
    **无公开 git 仓库、无 commit SHA**；2005 年后未再发布新版本
- 许可证：LGPL-2.1-or-later（上游 `COPYING` 为 LGPL-2.1；`README` 文字写作 "GNU GPL"，以 `COPYING` 为准）
- 语言 / 构建：C++ + autotools（预生成 `configure` + 手写 `GNUmakefile.in`）
- 产物：`bin/mkcue`（无库、无数据文件）

## 用法（上游 README:7-10）

```sh
mkcue                 # 读取 /dev/cdrom，列出全部音轨
mkcue /dev/cdrom1     # 指定设备
mkcue -t 12           # 只列前 12 条音轨（忽略数据轨）
```

## OHOS 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 2002 版 `build/config.guess` 不认 HarmonyOS，`configure` 在 `AC_CANONICAL_HOST` 阶段退出 | `0002-build-config.guess.patch` 增加 `*:HarmonyOS:*:*` 分支 → `aarch64-unknown-linux-ohos` |
| 2 | `build/config.sub` 不认 `aarch64`/`linux-ohos` | `0003-build-config.sub.patch` 增加 CPU 别名与 KERNEL-OS 组合 |
| 3 | HMDFS 上 `config.status` 用 `umask 077` 建临时目录失败（`Permission denied`），`config.h` 生成不出来 | `0004-configure.patch` 把 `umask 077` 改为 `022` |

`<linux/cdrom.h>` 与 `CDROM*` ioctl 由 OHOS SDK sysroot 提供，源码零改动。

## 依赖

Linux/OHOS 目标下**第三方依赖为 0**（链接行 `mkcue.o mb.o`，无任何 `-l`；
仅用 libc / libstdc++ / Linux 内核头）。详见 `1.0/reports/` 与 `mkcue-1-deps/DEPENDENCY-REPORT.md`。

## 测试

上游**没有自动化测试**（无 `tests/`、无 `check`/`test` 目标，见 `1.0/reports/upstream-test-entry.md`）。
`1.0/test_package/` 提供 9 例消费者验证（6 例上游行为 + 3 例鸿蒙平台），
**不能替代上游测试统计**。
