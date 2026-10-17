# paxctl

`paxctl` 是 PaX Team 的工具（GPL-2.0-or-later），用于**按可执行文件逐个**查询与
修改 PaX 的 ELF 程序头标志（`PT_PAX_FLAGS`）。

PaX 是内核级入侵防御机制，包含 `PAGEEXEC` / `SEGMEXEC` / `MPROTECT` / `RANDMMAP` /
`RANDEXEC` / `EMUTRAMP`。少数应用因设计或实现缺陷与之不兼容，需要按二进制豁免
某些强制策略；反向地，在"软模式"下也可以用 `paxctl` 为选定程序（网络守护进程、
处理网络数据的程序等）**打开**保护。

## Versions

| Version | Status | Assertions |
| --- | --- | --- |
| 0.9 | built | 74 |

Homepage: https://pax.grsecurity.net/

## 用法

```bash
# 查看某文件的 PaX 标志（12 字符标志串 + 逐条说明）
paxctl -v ./program

# 把 PT_GNU_STACK 程序头转换成 PT_PAX_FLAGS（就地改写）
paxctl -c ./program

# 新建 PT_PAX_FLAGS 程序头
paxctl -C ./program

# 禁用 / 启用单项保护（小写=禁用，大写=启用）
paxctl -m ./program        # 禁用 MPROTECT
paxctl -M ./program        # 启用 MPROTECT

# 恢复默认标志
paxctl -z ./program
```

> ⚠ **`-v` 与修改选项不要放在同一次调用**：实测 `paxctl -v -m f` 只查看、
> **不应用**修改（输出仍是改动前的标志串）。正确做法是先 `paxctl -m f`
> 再 `paxctl -v f`。这条陷阱已写入本包的路径 B 知识草稿。

```
$ paxctl -v -m ./fixture | grep 'PaX flags'
- PaX flags: -------x---- [./fixture]      ← 改动前
$ paxctl -m ./fixture && paxctl -v ./fixture | grep 'PaX flags'
- PaX flags: -----m-x---- [./fixture]      ← 改动后
```

## 12 字符标志串

每 2 字符一个槽：**偶下标 = "已启用"字母，奇下标 = "已禁用"字母**。

| 下标 | 0/1 | 2/3 | 4/5 | 6/7 | 8/9 | 10/11 |
| --- | --- | --- | --- | --- | --- | --- |
| 字符 | P/p | S/s | M/m | –/x | E/e | R/r |
| 功能 | PAGEEXEC | SEGMEXEC | MPROTECT | RANDEXEC | EMUTRAMP | RANDMMAP |

基准（`-c` 转换 + `-z` 复位后）恒为 `-------x----`。逐标志实测（每轮复位后单独施加）：

| 选项 | 标志串 | 选项 | 标志串 |
| --- | --- | --- | --- |
| `-p` | `-p-----x----` | `-P` | `P------x----` |
| `-e` | `-------x-e--` | `-E` | `-------xE---` |
| `-m` | `-----m-x----` | `-M` | `----M--x----` |
| `-r` | `-------x---r` | `-R` | `-------x--R-` |
| `-s` | `---s---x----` | `-S` | `--S----x----` |

组合：`-p -e -m -r -s` → `-p-s-m-x-e-r`；`-P -E -M -R -S` → `P-S-M--xE-R-`。

## OHOS 适配

| 项目 | 说明 |
| --- | --- |
| 目标 | `aarch64-linux-ohos`（musl）|
| 源码 | 单编译单元：`paxctl.c` 直接 `#include "paxctl-elf.c"` |
| 外部库 | 无（仅 `stdio`/`stdlib`/`unistd`/`getopt`/`elf`/`fcntl`/`errno`/`sys/mman`）|
| patch | 无 |
| 构建 | 直驱 clang：`clang -O2 -w -std=gnu99 -o paxctl paxctl.c` |
| 产物 | `bin/paxctl`（约 30 KB）；`share/man/man1/paxctl.1`、`share/doc/paxctl/README` |

上游 `Makefile` 用 `CC:=gcc` 且 `CFLAGS` 含 `-Wconversion` 等一长串告警开关，
在交叉编译环境既不可用也会被告警阻断，因此 `build()` 直驱 `clang`。

### 运行时说明

PaX 的**运行时**语义取决于内核是否为 grsecurity/PaX 内核以及其配置；OHOS 内核对
`PT_PAX_FLAGS` 的解释可能不适用。但 `paxctl` 的**文件读写行为**是纯用户态 ELF
操作（读程序头、改写程序头、回读校验），与内核无关，因此本包的验证聚焦于
**ELF 层面的确定行为**，这在本包 74 条断言中全部覆盖。

## 测试

上游**不含任何测试套件**：`Makefile` 只有 `all` / `install` / `clean` 三个目标，
**没有 `check` 或 `test` 目标**，源码 tarball 内也不含测试源文件。

`test_package/test_paxctl.c` 提供 **74 条断言**：

| 分组 | 条数 | 内容 |
| --- | --- | --- |
| 用法与错误路径 | 13 | 无参数 / `--help` / 非法选项 / 不存在文件 / 非 ELF 文件 / 未转换 ELF |
| `-c` 转换 | 5 | 转换提示、二次 `-c` 幂等、转换后不再提示缺少程序头 |
| 单标志 | 40 | 10 个标志 × (应用退出码 + 精确标志串 + 字符集形状 + 说明行一致性) |
| 组合标志 | 8 | 2 个组合 × 同上 4 项 |
| 复位不变量 | 3 | `-z` 从 3 种不同前置状态都回到基准串 |
| 夹具完好性 | 2 | 多轮改写后 `-v` 仍成功、仍是合法 ELF |
| scratch 可写性 | 1 | 显式探测（不假定 `/tmp`）|

两个关键设计：

- **夹具用被测程序自身的二进制副本**：`paxctl` 操作 ELF 程序头，任何本包产出的
  aarch64 ELF 都是合法输入。这样既不引入外部样本，又顺带证明"产物是结构完好、
  可被工具正确解析的 ELF"。
- **改动与读取分两次独立调用**：`paxctl -v -m f` 只查看不修改，合并调用会产生
  "断言恒等于基准串"的假通过。

判据全程用 `popen` 内存管道直读，**不写任何临时文件**；需要可写空间时只使用
`test()` 阶段创建于 `build_folder` 下的 scratch 目录（OHOS 上 `/tmp` 只读）。
