# prctl

`prctl` 是 `prctl(2)` 系统调用的命令行封装，用于**查询或控制进程行为**。

## Versions

| Version | Status | Assertions |
| --- | --- | --- |
| 1.7 | built | 71 |

Homepage: https://tracker.debian.org/pkg/prctl

## 用法

```
prctl [-v] [-h|--help] [--version] <-q|<options>> [command]

  Options:
      --unaligned=[silent|signal|default]
      --fpemu=[silent|signal|default]
      --mcekill=[early|late|default]
```

```bash
# 查询当前设置
prctl -q

# 设置并回显（-v 会打印确认信息）
prctl --mcekill=early -v

# 以指定设置 exec 一条命令
prctl --mcekill=late /usr/bin/your-daemon
```

## 平台差异（重要）

| 选项 | 上游标注 | 实际行为 |
| --- | --- | --- |
| `--unaligned=[silent\|signal\|default]` | **ia64 专有** | **运行期决定**：内核拒绝时打印 `ERROR: This platform does not implement set_unaligned prctl feature.` 并退出 **1**；内核接受时退出 **0**（`-v` 回显 `Set "unaligned" to "…"`）|
| `--fpemu=[silent\|signal\|default]` | **ia64 专有** | 同上（`set_fpemu`）|
| `--mcekill=[early\|late\|default]` | 架构无关 | 依赖内核是否支持 `PR_MCE_KILL` / `PR_MCE_KILL_GET` |

> ⚠ **同一二进制在不同内核上结果不同** —— 本包实测：
>
> | 环境 | `prctl(PR_SET_UNALIGN, …)` | 退出码 |
> | --- | --- | --- |
> | Ubuntu aarch64（WSL + qemu 本地验证） | 返回 `EINVAL` | **1** + `does not implement …` |
> | OpenHarmony CI worker | 返回 `0`（成功） | **0** + `Starting a shell` |
>
> 因此 `test_package` 对这两族选项采用**运行时分级断言**（两个分支各自断言），
> 而不是把某一端写死 —— 详见「测试」一节。这条经验已写入本包的路径 B 知识草稿。

实测（OpenHarmony 内核，选项被接受）：

```
$ prctl --unaligned=silent -v
Set "unaligned" to "silent"

$ prctl -q
Current settings for supported prctl operations:
mcekill      = default
```

> 注意区分两类失败（**退出码都是 1，但语义不同**）：
> - `--unaligned=bogus` → 打印**用法块**（参数校验拒绝；**所有平台一致**）
> - 内核拒绝 `--unaligned=silent` → 打印 **ERROR 行、不打印用法块**（参数合法，平台不实现）

## 退出码约定

| 调用 | 退出码 |
| --- | --- |
| `--version` / `-h` / `--help` | 0 |
| `-q`（查询） | 0 |
| 无参数 / 仅 `-v`（无动作） | **1** + 用法块 |
| 非法取值 | 1 + 用法块 |
| 非法选项（`--nope` / `-Z` / `--mcekill` 缺 `=`） | 1 + `prctl: invalid option …` |
| 内核拒绝的合法参数（平台不实现）| 1 + ERROR 行 |

## OHOS 适配

| 项目 | 说明 |
| --- | --- |
| 目标 | `aarch64-linux-ohos`（musl）|
| 源码 | 单 `.c`（`prctl.c` ~10.5 KB），**无 `config.h` 依赖** |
| 外部库 | 无（仅 `unistd`/`stdio`/`stdlib`/`getopt`/`errno`/`pwd`/`sys/prctl`/`string`）|
| patch | 无 |
| 构建 | 直驱 clang：`clang -O2 -w -std=gnu99 -o prctl prctl.c` |
| 产物 | `bin/prctl`（约 20 KB）；`share/man/man1/prctl.1` |

### 为什么不用上游 autotools

上游是 autotools 工程，但 tarball **不含生成的 `configure`**（只有 `configure.ac`
与 `Makefile.in`），交叉编译需要先 `autoreconf`；且 `configure.ac` 的 `AC_INIT`
仍是模板占位（`AC_INIT([FULL-PACKAGE-NAME], [VERSION], [BUG-REPORT-ADDRESS])`）。
由于 `prctl.c` 不依赖 `config.h`（版本串由源码内 `#define VERSION "1.7"` 提供），
`build()` 直驱 `clang` 即可，完全绕开 autotools 链路。

## 测试

上游**不含任何测试套件**：`configure.ac` / `Makefile.in` 中都没有 `check` 或 `test`
目标，源码 tarball 内也无测试源文件。

`test_package/test_prctl.c` 提供 **66 条断言**，按平台能力分三层：

### 第 1 层 —— 平台专有选项：**运行时分级断言**（两端都断言）

`--unaligned={silent,signal,default}` 与 `--fpemu={silent,signal}` 是否可用
**由内核运行期决定**，因此判据写成双分支，覆盖同一条不变量
「**合法取值必须得到明确结果，不得静默通过**」：

- **平台不实现** → 必须打印 `does not implement set_<feat> prctl feature` 且退出非 0；
- **平台实现** → 必须退出 0 且 `-v` 回显 `Set "<feat>" to "<val>"`。

测试会打印实际走了哪个分支（`[INFO] 平台实现 --unaligned` /
`[INFO] 平台不实现 --unaligned（退出码 1）`），便于在日志里区分环境差异。

> ⚠ 本包**首次提交时此处的 10 条断言在 CI 上失败**，原因是把本地内核
> （Ubuntu aarch64，返回 EINVAL）的行为写死成了"平台事实"，而 OpenHarmony 内核
> 实际接受该操作。改用双分支分级后，同一份判据在本地与 CI **都通过**。
> 完整复盘见路径 B 知识草稿 `DRAFT-PRCTL-PLATFORM-CAPABILITY-TIERED-ASSERTIONS`。

### 第 2 层 —— 能力探测 + 显式跳过

先用 `-q` 探测平台是否列出 `mcekill`：

```
  [INFO] mcekill 支持 = 是
── prctl --mcekill=early -v
  [PASS] --mcekill=early -v 退出码 (期望 0)
  [PASS] 回显 "Set "mcekill" to "early""
  [PASS] --mcekill=early 不报 Failed to
```

若平台未列出该操作，测试打印 `[SKIP]` 并**说明跳过原因**——绝不静默跳过，
否则"跳过"与"通过"在 CI 报告里无法区分。

### 第 3 层 —— 与平台无关的稳定基线（保持硬断言）

用法块完整性（必须列出全部三个选项名）、`--version`/`-h`/`--help` 退出码、
无动作时 `rc=1`、非法取值回落用法、非法选项报 `invalid option`。

判据全程用 `popen` 内存管道直读，**不写任何临时文件**（OHOS 上 `/tmp` 只读）。
