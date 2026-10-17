# 路径 B 知识库扩展申请：绕过上游 Makefile 直编时必须做「宏与 OBJ 契约核对」

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#7026 dds2tar 2.5.2
- **关联 PR**：`!9363`（`feat/dds2tar-2.5.2`，配方 PR）
- **知识草稿**：`knowledge/drafts/dds2tar-2.5.2-bypassing-makefile-macro-and-obj-parity.kv` / `.md`
- **草稿 ID**：`DRAFT-DDS2TAR-BYPASSING-MAKEFILE-MACRO-AND-OBJ-PARITY`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/dds2tar-2.5.2`）提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"

"绕过上游 Makefile、直接驱动编译器"是本仓库 raw-makefile 类配方的**主流做法**
（用于绕开隐式规则、`CC=cc -g` 这类把选项塞进编译器变量的写法、以及 autotools
交叉编译摩擦）。但上游 Makefile 同时是一份**构建契约**：它用命令行 `-D` 与变量把
源码分支所需信息注进去。**只读源码不读 Makefile，会连中三种症状相同表、根因不同的是
的失败**，把排查者引向三个互相独立、且都与真正原因无关的方向。

本条目把三者收敛成**一个可执行的核对清单**，可直接套用于任何 raw-makefile 配方；
并给出一个跨平台技巧（字符串宏改用生成头文件 + `-include`）以避免 shell 引号地狱。

## 二、三种失败形态（dds2tar 2.5.2 连中三坑）

| 漏项 | 症状 | 报错位置 | 会被误判为 |
|---|---|---|---|
| 字符串字面量宏 | `error: expected ';' after top level declarator` | 源码远处 | 源码语法不兼容 clang |
| 照抄特殊宏值 | `fatal error: '/usr/src/linux/…' file not found` | 头文件 | 缺内核源码，想伪造内核头 |
| 跨续行的 OBJ 成员 | `ld.lld: error: undefined symbol: zfopen` | **链接期** | 缺库/符号问题 |

### 坑 1：`CCFLAGS=-DVERSION=\"$V\"`（字符串字面量宏）

```c
static const char version[] = "Version " VERSION " -- last change 1994 Dez 22.";
```

宏未定义 → 标识符留在表达式里 → 在第 147 行报语法错误，而真正原因在 Makefile 第 73 行。

**不要靠 shell 引号转义**（`-DVERSION=\"2.5.2\"` 在 cmd.exe 与 POSIX sh 下行为不同），
改为生成内联头文件 + `-include`：

```python
hdr = os.path.join(src, "_dds2tar_version.h")
with open(hdr, "w", encoding="utf-8") as f:
    f.write('#ifndef DDS2TAR_VERSION_H\n#define DDS2TAR_VERSION_H\n'
            '#define VERSION "2.5.2"\n#endif\n')
cflags += f' -include {hdr.replace(os.sep, "/")}'
```

### 坑 2：默认宏值触发**宿主机内核源码绝对路径** include

```c
/* dds2tar.h */
#if defined ST_BUFFER_BLOCKS && ST_BUFFER_BLOCKS == 0
#undef ST_BUFFER_BLOCKS
#include "/usr/src/linux/drivers/scsi/st_options.h"
#endif
#ifndef ST_BUFFER_BLOCKS
#define ST_BUFFER_BLOCKS 32
#endif
```

上游 Makefile 默认 `BUFFER=-DST_BUFFER_BLOCKS=0`，即**刻意**去引宿主机内核头。
正确处置：**刻意不定义该宏**，让 `#ifndef` 兜底取 32（Makefile 注释
*"The value of the kernel is normally ST_BUFFER_BLOCKS=32"* 已认可该值）。

### 坑 3：`OBJ` 跨续行

```make
OBJ= dds_index.o dds_extract.o dds_tape.o dds_quote.o \
     zf-cre-open.o dds_chkhdr.o
```

只读第一行会漏 `zf-cre-open.o`（`reopen/creopen/zfopen/cclose`）与
`dds_chkhdr.o`（`dds_is_tar_header_record`）——编译全过，**只在链接期**报
undefined symbol；而漏掉的恰是"次要功能"模块，最易被忽略。

## 三、可复用做法：动手前的「Makefile 契约核对」三件事

```bash
# ① 完整展开跨续行变量
awk '/^OBJ=/{f=1} f{print; if($0 !~ /\\$/) exit}' Makefile
# ② 枚举全部命令行宏
grep -nE '^\s*[A-Z_]+\s*=-?D' Makefile
# ③ 反向判断：某个宏取值会让源码 include 宿主机绝对路径 → 不要注入该值
grep -rn '/usr/\|/usr/local\|/opt/' *.h *.c | head
```

逐宏判定：**源码是否依赖它？依赖则必须注入；不注入也要显式确认有兜底。**

## 四、验证证据

| 项 | 证据 |
|---|---|
| 坑 1 复现 | 首轮本地 `conan create`：`dds2tar.c:147:11: error: expected ';' after top level declarator` |
| 坑 2 复现 | 补上 `-DST_BUFFER_BLOCKS=0` 后：`./dds2tar.h:12:10: fatal error: '/usr/src/linux/drivers/scsi/st_options.h' file not found` |
| 坑 3 复现 | 去掉该宏后：`ld.lld: error: undefined symbol: reopen / creopen / zfopen / cclose / dds_is_tar_header_record` |
| 全部修复后 | `conan create archives/d/dds2tar/2.5.2` **退出码 0**，`Package created`，test_package 编译通过 |
| 参考实现 | `archives/d/dds2tar/2.5.2/conanfile.py`（含生成的 `_dds2tar_version.h` 注入写法） |

## 五、查重声明

- **E392**（Raw makefile Conan 配方的三个通用陷阱：BadZipFile 编码器误选 /
  `compiler_executables` 字典获取 / make 默认 cwd 错误）：E392 讲"**调用 make 本身**"
  的陷阱；本条讲"**绕过 make 直编**"时与 Makefile 的**契约不等价**。症状集合
  （语法错误 / 宿主机头 / 链接符号）与处置方式完全不同，**不合并**。
- **E483 / E276**（`get()` 对无扩展名 URL 报 BadZipFile）：属取源阶段，无关。
- 正式库以 `st_options.h` / `CCFLAGS` / `undefined symbol: zfopen` 检索无命中。

## 六、请评审确认

1. 是否认可本条目为**路径 B（贡献创新，10 分候选）**评审对象？
2. 是否建议把「Makefile 契约核对三件事」写入 `docs/ADAPTATION_GUIDE.md`
   的 raw-makefile 配方章节（或 `references/`）作为强制前置步骤？
3. 「刻意不定义某个宏，让源码 `#ifndef` 兜底」这一处置是否被认可为对宿主机
   依赖的合规规避（而非"跳过构建步骤"）？本包已在 `notes.md` 显式记录取舍依据。
