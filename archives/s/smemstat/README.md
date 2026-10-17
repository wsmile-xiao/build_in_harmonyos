# smemstat

Kernel memory usage reporter — samples `/proc/meminfo` and per-process memory
accounting and renders the result in an ncurses display.

- 上游仓库: https://github.com/ColinIanKing/smemstat
- 版本: 0.02.13（上游 tag `V0.02.13`）
- 许可证: GPL-2.0-only（`COPYING`）
- 类型: 命令行工具（`bin/smemstat`，R38 已附 `commands.json`）
- 构建系统: make（纯 Makefile，无 configure）

## 用途

- 单次/连续内存快照：`smemstat [duration] [count]`，支持 KB/MB/GB 单位（`-k/-m/-g`）
- 变化趋势展示：`-a` 上下箭头、`-t/-T` top 模式只看内存变化/大户
- 进程过滤与命名：`-p proclist`、`-c` comm 名、`-l/-s` 长/短命令行
- JSON 导出：`-o file` 输出快照数据（配合 `-q` 静默）

## OHOS 适配要点

- 链接依赖 `-lm -lncursesw`：ncurses/6.6（ohpcd 制品仓静态宽字符构建）提供 `libncursesw`
- 纯 Makefile 直驱：命令行完整重供 `CFLAGS`（含 `-DVERSION` 引号形态），见软件级 `manifest.yaml`
- 无 `make install`：HMDFS 上以纯 Python 拷贝完成 staging
