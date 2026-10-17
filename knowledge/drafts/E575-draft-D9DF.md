# E575 — raw Makefile 配方用 make 命令行变量传 CFLAGS 时，字符串宏必须两级反斜杠转义

> Contributor: Awstme <awstme@qq.com> | Status: Draft | Updated: 2026-09-11
> Source: cycfx2prog 0.47 适配（原生 make 首轮版本宏退化成 `double`，`-Wformat` 是唯一信号）

## 编号说明

与同批草稿 E574 相同口径：跨 worktree 文件形态扫描（含 `DRAFT-<ID>-*`）∪ 主线文本引用
整词扫描（剔除 sha256/URL 子串假命中）后，`E543`–`E574` 全部占用，**最小空号 = E575**。
创建后回查无同 ID 不同后缀的并发草稿。

## 错误特征

编译**成功、退出码 0**，只有一条告警（clang；gcc 措辞不同）：

```text
clang -DPROBE_VERSION="1.2" probe.c -o probe
probe.c:2:41: warning: format specifies type 'char *' but the argument has type 'double' [-Wformat]
int main(void) { printf("version %s\n", PROBE_VERSION); return 0; }
                                 ~~     ^~~~~~~~~~~~~
                                 %f
<command line>:1:23: note: expanded from here
#define PROBE_VERSION 1.2          ← 宏退化成数值常量，不再是被引号包裹的字符串
                      ^~~
--- run:
version o<EF BF BD><EF BF BD><EF BF BD>   ← 运行期把 double 当 char* 解引用，打印内存垃圾；rc=0
```

**判据**：`#define <NAME> <数值>`（没有引号）而不是 `#define <NAME> "…"`。这条告警是
**唯一**线索——程序中招；若上游没带 `-Wformat`（或告警被忽略），编译与运行都"全绿"，
只有断言自报版本号/构建号的功能测试能发现。

## 触发条件

- 构建系统: 上游手写 Makefile（`CFLAGS`/`LDFLAGS` 用 `=` 赋值，因此必须用 make **命令行
  变量**覆盖；同名环境变量会被 makefile 赋值覆盖）
- 阶段: compilation
- 被覆盖的 flags 含 `-D<NAME>=\"<字符串>\"` 形态的字符串宏（版本号、构建号、日期、路径）

## 根因分析

命令行变量的值会被 shell 解析**两次**：

```text
配方 Python 字符串 → shell(调用 make) → make 变量 → recipe shell → 编译器 argv
                       ↑ 第 1 层解析              ↑ 第 2 层解析
```

- 上游 Makefile 内部写 `CFLAGS = -DPROBE_VERSION=\"1.2\"` 时，make 把 `-DPROBE_VERSION=\"1.2\"`
  原样交给 recipe shell，第 2 层把 `\"` 还原成 `"` → 编译器收到 `-DPROBE_VERSION="1.2"` → 正确。
- 配方用命令行变量覆盖时，如果写成 shell **双引号**包裹的 `-DPROBE_VERSION=\"1.2\"`，
  反斜杠在**第 1 层**就被吃掉，make 变量里只剩 `-DPROBE_VERSION="1.2"`；第 2 层再把这
  一对引号剥掉 → 编译器收到 `-DPROBE_VERSION=1.2` → 宏变成 `double`。

换句话说：命令行变量路径上，配方必须**自己**提供那一层反斜杠，且调用 shell 不能吃掉它。

## 最小复现探针（实测原始输出）

`probe.c`：

```c
#include <stdio.h>
int main(void) { printf("version %s\n", PROBE_VERSION); return 0; }
```

`Makefile`（复刻上游 `=` 赋值形态）：

```make
CC = gcc -pipe
CFLAGS = -DPROBE_VERSION=\"1.2\"
all: probe
probe: probe.c
	$(CC) $(CFLAGS) probe.c -o probe
```

三种调用方式实测：

```text
=========== case A: 单级转义（shell 双引号，反斜杠在调用 shell 就被吃掉）
clang -DPROBE_VERSION="1.2" probe.c -o probe
probe.c:2:41: warning: format specifies type 'char *' but the argument has type 'double' [-Wformat]
<command line>:1:23: note: expanded from here
#define PROBE_VERSION 1.2
--- run:
version o<EF BF BD><EF BF BD><EF BF BD>     ← 垃圾输出，rc=0

=========== case B: 两级转义（shell 单引号，反斜杠留给 make 与 recipe shell）
clang -DPROBE_VERSION=\"1.2\" probe.c -o probe
--- run:
version 1.2                            ← 正确

=========== 对照：不覆盖 CFLAGS（让上游 Makefile 自己的 CFLAGS 生效）
clang -DPROBE_VERSION=\"1.2\" probe.c -o probe
--- run:
version 1.2                            ← 同样正确（说明问题只出在命令行变量这一层）
```

日志：`~/tmp/cycfx2prog-0.47/evidence/quote-probe.log`（探针源码与 `run.sh` 同目录）。

## 解决方案

### 推荐方案

让反斜杠活到 make 变量里，并放在 shell **单引号**参数中：

```python
cflags += ['-DCYCFX2PROG_VERSION=\\"%s\\"' % self.version]   # Python 源码里是 \" 两字符
command = "make -j1 CC='{cc}' CFLAGS='{cflags}'".format(...)  # 单引号保护反斜杠
self.run(command, cwd=self.source_folder, env="conanbuild")
```

日志自检（cycfx2prog 实测，正确形态）：

```text
clang -pipe -c -O3 -DNDEBUG ... -DCYCFX2PROG_VERSION=\"0.47\" cycfx2prog.cc
$ ./cycfx2prog --version
cycfx2prog version 0.47
```

### 回退方案

放弃命令行变量覆盖，改为给上游 Makefile 打正式补丁引入追加式变量
（`CFLAGS += $(EXTRA_CFLAGS)`），把字符串宏留在 Makefile 内原有的 `\"` 形态里。
代价是引入补丁；仅在配方无法控制调用 shell 引号时使用。

## 与既有条目的差异

与 E573（`GnuToolchain.defines` 返回裸宏名，缺 `-D` 前缀）同属"raw Makefile 配方手工拼
CFLAGS"家族，但**不是同一模式**：

| | E573 | E575（本条） |
|---|---|---|
| 触发点 | `tc.cflags + tc.defines` 直接相加 | 命令行变量里的字符串宏转义层级 |
| 失败形态 | 编译**失败**：`clang: error: no such file or directory: 'NDEBUG'` | 编译**成功**，运行期输出垃圾 |
| 首要信号 | clang 错误行（指向源文件名） | `-Wformat` 告警（容易被忽略） |
| 修复 | 逐项补 `-D` 前缀 | 补一层反斜杠转义 + shell 单引号 |

两者的共同前置条件相同（上游 Makefile 用 `=` 赋值 → 必须走命令行变量），因此实际项目
里可能**同时**出现；建议按"先补 `-D` 前缀让它编过，再补转义让它输出正确"的顺序排查。

## 验证证据

- 探针三种调用方式的原始输出见上文（`quote-probe.log`）；
- cycfx2prog 0.47 实际适配：修正转义后原生 `make` rc=0、`./cycfx2prog --version` 输出
  `cycfx2prog version 0.47`、`--list` rc=0、无参数 rc=1；`conan create` rc=0，
  test_package 33/33（其中第 5 条断言正是"版本行精确等于 `cycfx2prog version 0.47`"，
  用于守住本模式的回归）。
