# 知识库拓展：大小写不敏感文件系统上中间产物与源文件撞名

> 样例演示库：`archives/m/mbr/1.2.2`（本目录即其知识库拓展产物，随库适配同 PR 提交）
> 相关补丁：`../patches/0001-case-distinct-intermediate-suffix.patch`
> 检测脚本：`detect-case-insensitive-build.sh`　复现脚本：`reproduce.sh`　处理策略：`strategy.md`

## 1. 一句话

上游构建规则用**只差大小写**的两个后缀表示「源文件 → 中间产物」（如 `%.s86: %.S86`、
`y2k.s86: mbr.S86`）。在大小写不敏感的文件系统上，这两个名字解析到**同一个文件**：make 对
中间产物 `mbr.s86` 的存在性检查被源文件 `mbr.S86` 满足，于是「源 → 中间产物」的配方**根本
不执行**，汇编器被直接喂入**未预处理**的源码，报出一批与语法毫无关系的错误——mbr 1.2.2 实测
为 as86 的 **87 处 `unbound label`**（`make` 退出码 2）。

## 2. 识别条件（两条同时满足即命中）

1. **文件系统**：构建目录位于大小写不敏感的卷上。
   鸿蒙 PC 上 `/storage/hmdfs` 即为此类（`tmpfs` 挂载的 HMDFS）：写入 `CaseProbeTest.txt` 后
   `caseprobetest.txt` 命中的是同一个文件。vfat、默认 NTFS、macOS 默认 APFS 同理。
2. **构建规则**：规则的目标与前置**只差大小写**，常见三种形态：
   - 后缀/模式规则：`%.<x>: %.<X>`（`tolower(<x>) == tolower(<X>)`）
   - 显式规则：`<name>.<x>: <name>.<X>`（同 basename）
   - 任意规则行：`<t>: <p>` 且 `t != p` 但 `tolower(t) == tolower(p)`

`detect-case-insensitive-build.sh <源码目录>` 自动完成这两步判定（可接在 CI / 适配前评估阶段，
命中时退出码 1）。

## 3. 为什么在鸿蒙 PC 上必现

- HMDFS 大小写不敏感 ⇒ `%.s86: %.S86` 的目标与前置是同一 inode（`stat("mbr.s86")` 命中
  `mbr.S86`）。实测后果是**配方被跳过**：make 认为中间产物「已存在且是最新的」，规则体
  `$(CC) -E -xc $< -o $@.tmp && mv $@.tmp $@` 一次都不执行，as86 被直接喂入原始 `.S86` 源码
  （10562 B），报 87 处 `unbound label`；源文件本身未被改动（与 tarball 原文件 `cmp` 一致）。
  推论：即便改了条件让配方真的执行，`mv $@` 也会落到同一个 inode 上、把源码替换成预处理
  结果——两条路都走不通，只能把中间后缀改名。
- 现象高度误导：报错来自汇编器（`unbound label`），容易被误判为「汇编器不支持」「x86 汇编
  不可适配」。实测：把同一 `mbr.S86` 手工 `clang -E -xc` 后交给 as86，rc=0、0 错误，证明
  汇编链路本身没问题。
- 与既有知识条目的方向不同：E320 / E485 / E407 属「探测成功但运行期不可用」，
  E537 属「链接期缺 SONAME」；本条是**构建规则语义层面的失效**，故单列。

## 4. 处理策略

见 `strategy.md`，三条递进：

| 策略 | 适用 | 代价 |
|---|---|---|
| S1 改中间后缀（样例采用） | 规则可在补丁中改（Makefile.am/.in、CMake 等） | 最小，产物字节不变 |
| S2 源码树只读 + 输出目录分离 | 规则由生成器写死、不宜打补丁 | 需验证隐式规则不落回源码树 |
| S3 `env_unsupported` 标记 | 无法在配方内规避 | 如实上报 + 复现证据 |

此外，本样例同时覆盖**第二类共性素材**：构建期需要**非目标架构**的工具（本例 as86/ld86 与
xxd）时，用 `tool_requires` 从制品仓补齐即可，x86 汇编 ≠ 不可适配（见 `strategy.md` §4）。

## 5. 复现与验证

```sh
# 检测（先判定是否命中）
sh detect-case-insensitive-build.sh /path/to/src  detect.log

# 复现 + 验证（阶段 A 未修复 → 预处理配方不执行、as86 报错；阶段 B 应用策略 → 配方正常执行、构建通过）
sh reproduce.sh /path/to/src  "${TMPDIR:-/tmp}/mbr-case-repro"  "${TMPDIR:-/tmp}/mbr-case-repro/logs"
```

`reproduce.sh` 全程把输出重定向到日志文件（不使用 `| head`，规避 SIGPIPE），并逐阶段打印
退出码与关键计数（`unbound label` 条数、预处理配方执行次数、`mbr.b` 字节数、源文件是否被改动）。

## 6. 样例库实测数据（mbr 1.2.2，HarmonyOS PC aarch64）

| 阶段 | 结果 |
|---|---|
| A 未修复 | `make rc=2`；预处理配方执行 0 次；as86 报 87 处 `unbound label`；`mbr.S86` 未被改动 |
| B 应用 S1 | `configure rc=0`、`make rc=0`；预处理配方执行 3 次、as86 0 报错；`mbr.b` 512 B、`install-mbr` 39296 B；`mbr.S86` 未被改动 |
| 手工对照 | 同一 `mbr.S86` 手工 `clang -E -xc` 后交给 as86：rc=0、0 错误（证明汇编链路本身正常） |

完整构建与测试结论见 `../reports/test-report.md`。
