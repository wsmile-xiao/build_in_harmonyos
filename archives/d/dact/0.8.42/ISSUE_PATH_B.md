# 路径 B 知识库扩展申请：直编 autoconf 项目的两处隐蔽前提（config.h 门控 + 功能表自洽）

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#6981 dact 0.8.42
- **关联 PR**：`!9424`（`feat/dact-0.8.42`，配方 PR）
- **知识草稿**：`knowledge/drafts/dact-0.8.42-autoconf-direct-build-hidden-premises.kv` / `.md`
- **草稿 ID**：`DRAFT-DACT-AUTOCONF-DIRECT-BUILD-HIDDEN-PREMISES`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/dact-0.8.42`）提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"

本仓库大量包的上游是 autoconf，而"绕过 configure 直编"是主流做法。但直编与
configure **并不等价**，本条给出两处会让等价关系悄悄崩塌的前提，且其中一处的失败
形态是**编译链接全过、功能静默缺失**（比链接失败更危险）：

1. **`config.h` 的包含被 `HAVE_CONFIG_H` 门控** —— 忘了 `-D` 则生成的 config.h
   永不被包含，全部能力宏失效；
2. **能力宏必须与位置敏感的功能注册表严格自洽** —— 错配会导致"未定义符号"
   或更糟的"静默功能缺失"。

附带的 `AC_REPLACE_FUNCS` 与 musl 差异（`getpass` 不声明）也一并给出判据。

## 二、前提一：`config.h` 未被包含（门控）

```c
#ifdef HAVE_CONFIG_H
#include "config.h"
#endif
```

判据：`grep -rn 'HAVE_CONFIG_H' *.h`

本包实测：首次构建前即按此检查并传了 `-DHAVE_CONFIG_H`；若漏掉，症状会是标准
POSIX 符号 `undeclared`，**与"config.h 写错"无法区分**。

## 三、前提二：能力宏 ↔ 位置敏感注册表的严格对偶

`algorithms.h` 是一张 256 项、**按下标注册**的函数指针表，逐项按宏在
"真实实现 / `DACT_FAILED_ALGO`" 之间切换。因此：

| 错配 | 后果 | 可见性 |
|---|---|---|
| 定义了宏却没编对应 `.c` | `undefined symbol: comp_xxx_algo` | 易发现 |
| 没定义宏（走占位）但能编的实现也没编 | 编译链接全过，**算法运行时静默不可用** | **难发现** |

本包做到严格对偶（`HAVE_LIBZ` ↔ `comp_zlib/comp_mzlib/comp_mzlib2`；未启用
`HAVE_LIBBZ2`/`DEBUG` ↔ 不编译对应模块），并额外查明 `comp_lzoox/lzooy/lzota.c`
在未启用时是**编译期宏别名**（`#define comp_lzoX_algo DACT_FAILED_ALGO`），无需编译。

## 四、附带：`AC_REPLACE_FUNCS` 与 musl 不声明 `getpass`

```m4
AC_REPLACE_FUNCS(getopt strsep getpass mkstemp uname)
```

语义是"libc 有就定义 `HAVE_X`，没有就编随包同名 `.c`"。OHOS musl 的
**`<unistd.h>` 完全没有 `getpass` 声明**（glibc 会声明；musl 仅 `_GNU_SOURCE` 下才有），
故保持 `HAVE_GETPASS` **未定义**并编译随包 `getpass.c`。

首次构建的真实报错（**极具误导性**）：

```
ui.c:165:6: error: incompatible integer to pointer conversion
            assigning to 'char *' from 'int' [-Wint-conversion]
```

看起来像"1990 年代老代码不兼容 clang 15"，实为 musl 头文件差异。

## 五、可复用清单（动手前三条 grep）

```bash
grep -rn 'HAVE_CONFIG_H' *.h                                   # ① 是否需要 -DHAVE_CONFIG_H
grep -rn 'AC_REPLACE_FUNCS\|AC_CHECK_LIB.*main' configure.in    # ② 哪些函数/库走"有则用、无则编"
grep -n 'algorithms\[\|_algo,' *.h                             # ③ 是否存在位置敏感功能表
```

## 六、验证证据

| 项 | 证据 |
|---|---|
| 首轮失败 | `ui.c:165: error: incompatible integer to pointer conversion assigning to 'char *' from 'int'`（getpass 隐式声明） |
| 修复 | 不定义 `HAVE_GETPASS` + 编译随包 `getpass.c` → 本地 `conan create` **退出码 0** |
| 构建路线 | 不跑 configure，直编复刻 upstream static 模式（CORE_OBJS 16 项 + ALGO_OBJS 10 项） |
| 产物 | `ELF64 / AArch64`，`DT_NEEDED` **仅 libc.so**（zlib 静态链入，G3 系统库隔离达标） |
| 消费者测试 | 6 条断言（存在/可执行/架构/`-h` 真实执行+usage 字面/`dact.conf` 安装/`-V` 真实执行） |
| 测试判据加固 | 按 AI 检视 P2/P3：`126/127/>=128` 一并视为"没跑起来"；循环读干管道才 `pclose` |

## 七、查重声明

- **cpmtools**（同批）：那条是"config.h **内容**必须与 config.h.in 完全 parity（宏与
  `#include` 成对写在内部）"；本条是"config.h **压根没被包含**（门控未开）"。判据
  （`grep HAVE_CONFIG_H` vs `grep -c '^#include' config.h`）与处置均不同，**不合并**。
- **dds2tar**（同批）：讲 Makefile 的命令行宏与 OBJ 契约；本条讲头文件门控与
  **运行时注册表自洽性**（可在编译全过时造成功能静默缺失），**不合并**。
- **cvs-fast-export**（同批）：生成产物 vs 再生成规则，无交集。
- 正式库以 `HAVE_CONFIG_H` / `AC_REPLACE_FUNCS` / 位置敏感注册表检索无相关条目。

## 八、申请分值

**路径 B【知识库扩展】贡献创新：10 分候选**

理由：本条沉淀的是 autoconf 项目直编的**结构性前提**（含一处"编译全过但功能静默
缺失"的高危形态），给出三条可执行 grep 判据与"宁少勿多"的对偶原则，跨库可复用；
全部结论来自本包真实构建证据与原始报错。

- **路径 A**：分值随本配方 PR（`!9424`）正常申报。
- **测试框架/工具链验证**：作为路径 B 的**证明材料**，**不重复申报额外分值**（最终以官方审核为准）。
- **路径 C（高难度挑战）**：**不申报** —— 本包为 39 文件 autotools 压缩工具，
  未强绑定私有接口/私有编译工具链/汇编或闭源二进制，依赖链亦不庞大（依赖闭包
  仅 `zlib/1.3.1`），Curator 四条件全否。
- **依赖库附加分**：**不申报** —— 依赖 `zlib/1.3.1` 为仓内既有已发布包，闭包完整，
  无新增外部依赖缺口需要先行适配。
- **路径 B 配额**：本 run 内按平台配额交付（本 Issue 占 1 条）。

## 九、请评审确认

1. 是否认可本条目为**路径 B（贡献创新，10 分候选）**评审对象？
2. 是否建议把这三条 grep 判据（`HAVE_CONFIG_H` 门控 / `AC_REPLACE_FUNCS` /
   位置敏感注册表）写入 `docs/ADAPTATION_GUIDE.md` 的 autoconf 直编章节？
