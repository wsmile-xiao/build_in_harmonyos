# DAZZ_DB (dazzdb)

DAZZ_DB 是 Gene Myers 为 Dazzler 长读段组装器设计的**压缩读段数据库**：把
PacBio/ONT 的 fasta（以及 quiva/arrow 质量值流）装载成单个可见的 `FOO.db`
存根加上若干隐藏的次级文件（`.FOO.idx` 索引、`.FOO.bps` 序列、`.FOO.qvs`
quiver 质量值、`.FOO.arw` arrow 脉冲宽度、`.FOO.<track>.anno/.data` 自定义轨），
让组装流程可以丢弃原始 fasta 而仍能逐字节还原，并把数据按块（block）切分以便
并行计算。

## 功能概述

本包安装上游 Makefile 的全部 21 个命令行工具：

| 分类 | 工具 |
|------|------|
| 建库与互转 | `fasta2DB` `DB2fasta` `quiva2DB` `DB2quiva` `arrow2DB` `DB2arrow` `fasta2DAM` `DAM2fasta` `DB2ONE` |
| 查询与统计 | `DBshow` `DBstats` |
| 分块与掩码 | `DBsplit` `DBtrim` `DBdust` `Catrack` |
| 库管理 | `DBrm` `DBmv` `DBcp` `DBwipe` |
| 合成数据 | `rangen`（随机参考基因组） `simulator`（按覆盖度采样读段） |

典型流程（上游 README 的完整示例）：

```
rangen 1.0 > R.fasta            # 1 Mbp 随机参考基因组
fasta2DAM R R.fasta             # 装入 .dam
simulator R -c20. > G.fasta     # 采样 20x 读段
fasta2DB G G.fasta              # 建压缩读段库 G.db
DBsplit -s11 G                  # 按 ~11 Mbp 切块
DBdust G.1 ; DBdust G.2
Catrack G dust                  # 合并成整库掩码轨
DBstats -mdust G
```

## OHOS 适配

- **构建**：上游手写 Makefile 的 21 条规则全部硬编码 `gcc`，其中 20 条还写死 `-lm` 或 `-lz`
  （21 条中 18 条带 `-lm`、2 条带 `-lz`，交集为空，`rangen` 两者皆无），鸿蒙 toolchain 只有 clang。补丁 0001 把每条
  规则改为 `$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ <原有源文件列表> $(LDFLAGS) $(LDLIBS)`
  （逐条保留源文件而不是用 `$^`，避免把 `.h` 带进编译命令），配方通过 conanbuild
  环境注入 CC 与 zlib 路径。
- **libc 边界**：OHOS libc 导出 `index` 但不导出 BSD 遗留别名 `rindex`，链接期
  报 `undefined symbol: rindex`。补丁 0002 统一改用 POSIX `strrchr`。
- **只读 /tmp**：`ONElib.c` 把模式临时文件硬编码到 `/tmp`，设备上 `/tmp` 是只读
  挂载（`errno=30 EROFS`），所有基于 ONElib 的工具（如 `DB2ONE`）一运行就 abort。
  补丁 0003 改为运行时探测可写目录（`$TMPDIR` → `/tmp` → `$HOME` → cwd）并把
  路径缓冲区改为有界 `snprintf`。
- **zlib（仅链接期）**：上游 Makefile 为 `arrow2DB`/`DB2arrow` 写了 `-lz`，但本版本源码
  **不使用 zlib**（全树无 `#include <zlib.h>`、无 zlib API 调用，产物未定义符号只有 libc）。
  配方仍声明 `zlib/1.3.1`，使 `-lz` 解析到包内静态库而不是 OHOS sysroot 的桩 `libz.so`，
  打包产物因此不带 `libz.so` 依赖（`NEEDED` 只有 `libc.so`）。
- **上游缺陷**：`DB2arrow` 缺 `Open_Arrow()` 调用（对任何 A-DB 必然失败）、
  `DBstats -m<track>` 循环内 use-after-free、`DB2ONE` 无参数时越界写命令行副本，
  分别由补丁 0005/0006/0004 修复。
- **测试**：上游**没有测试套件**（Makefile 无 check/test 目标，源码树无测试文件），
  因此上游用例数记 0；适配侧 `test_package/test.sh` 以 93 项断言驱动全部 21 个
  工具，覆盖数据通路、逐字节往返、质量值两条支路、掩码轨、库生命周期与临时目录
  探测四种边界。

已知差异：Debian 为避让 `/usr/bin/simulator` 命名冲突把该工具改名为 `dsimulator`；
本包安装到 Conan 包内独立 `bin/` 目录，保留上游原名。`DBsplit`/`DBtrim` 带交互
确认提示（`[Y/N]`）；`rangen` 的长度参数单位是 Mbp。

## 依赖关系

| 类型 | 依赖 |
|------|------|
| 链接依赖 | zlib（仅链接期：满足上游 Makefile 的 `-lz`；本版本源码不调用 zlib API） |
| 运行依赖 | libc（musl）——打包产物 `NEEDED` 只有 `libc.so`，libm 亦并入 libc |
| 下游用途 | Dazzler 组装器（daligner 等）读取 `.db`/`.dam`；也可独立做 fasta ⇄ DB 转换与统计 |

## 参考资料

- 上游仓库与源码：<https://github.com/thegenemyers/DAZZ_DB>
- 命令指南（上游作者博客）：<https://dazzlerblog.wordpress.com/command-guides/dazz_db-command-guide>
- 源码快照：commit `a3eefd4e3b31b6701f57268f8353e136a6f80525`（2025-02-17），
  与 Debian 源码包 `dazzdb 1.0+git20250217.a3eefd4-1` 的 orig tarball 树一致
- 许可：BSD-3-Clause（Copyright (c) 2014, Dr. Eugene W. Myers）
