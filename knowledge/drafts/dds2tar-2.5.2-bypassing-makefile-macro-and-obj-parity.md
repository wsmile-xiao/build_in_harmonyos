# 绕过上游 Makefile 直编：必须做「宏与 OBJ 契约核对」（三种失败形态）

> Draft: `DRAFT-DDS2TAR-BYPASSING-MAKEFILE-MACRO-AND-OBJ-PARITY`
> Stem: `dds2tar-2.5.2-bypassing-makefile-macro-and-obj-parity` — 与同 stem 的 `.kv` 成对
> 实例：dds2tar 2.5.2（PR !9363，三个坑在同一个包里连中）

## 基本信息

- **ID**: DRAFT-DDS2TAR-BYPASSING-MAKEFILE-MACRO-AND-OBJ-PARITY
- **严重度**: 2
- **类别**: conan, raw-makefile, cross-compile, recipe-parity
- **触发工具**: conan
- **阶段**: build

## 为什么把三种症状写进一条

三者**根因同一**（没有把上游 Makefile 当作"构建契约"来复刻），但**失败形态与排错方向
完全不同**——若不先做契约核对，会在三条错路上各烧一轮 CI：

| 漏项 | 症状 | 报错位置 | 错误排错方向 |
|---|---|---|---|
| 字符串字面量宏 | `error: expected ';' after top level declarator` | 源码远处 | 以为源码语法不兼容 clang |
| 照抄特殊宏值 | `fatal error: '/usr/src/linux/…' file not found` | 头文件 | 以为缺内核源码、想伪造内核头 |
| 跨续行的 OBJ 成员 | `ld.lld: error: undefined symbol` | **链接期** | 以为缺库/符号问题 |

## 实例：dds2tar 2.5.2 连中三坑

上游 Makefile 的关键片段：

```make
V=2.5.2
HPDAT=-DHPDAT
BUFFER=-DST_BUFFER_BLOCKS=0            # ← 特殊值，见坑 2
CC=cc -g
CCOPT=$(HPDAT) $(EXP_STUFF) $(BUFFER) -DDEVICE=\"$(DEVICE)\" -O4 -Wall $(TRACE)
CCFLAGS=-DVERSION=\"$V\"                # ← 字符串字面量宏，见坑 1
OBJ= dds_index.o dds_extract.o dds_tape.o dds_quote.o \
     zf-cre-open.o dds_chkhdr.o        # ← 跨续行，见坑 3
```

### 坑 1：`-DVERSION=\"2.5.2\"` 是**字符串字面量宏**

```c
static const char version[] = "Version " VERSION " -- last change 1994 Dez 22.";
```

宏未定义 → 标识符 `VERSION` 留在表达式里 → `error: expected ';' after top level declarator`
（报错在第 147 行，而真正原因在 Makefile 第 73 行）。

**并且不要用 shell 引号转义**：`-DVERSION=\"2.5.2\"` 在 cmd.exe 与 POSIX sh 下行为
不同，跨平台配方会时通时不通。**正确做法：生成一个内联头文件，用 `-include` 注入**：

```python
hdr = os.path.join(src, "_dds2tar_version.h")
with open(hdr, "w", encoding="utf-8") as f:
    f.write('#ifndef DDS2TAR_VERSION_H\n#define DDS2TAR_VERSION_H\n'
            '#define VERSION "2.5.2"\n#endif\n')
cflags += f' -include {hdr.replace(os.sep, "/")}'
```

### 坑 2：`-DST_BUFFER_BLOCKS=0` 会去引**宿主机内核源码绝对路径**

```c
/* dds2tar.h:10 */
#if defined ST_BUFFER_BLOCKS && ST_BUFFER_BLOCKS == 0
#undef ST_BUFFER_BLOCKS
#include "/usr/src/linux/drivers/scsi/st_options.h"   /* 宿主机内核源码 */
#endif
#ifndef ST_BUFFER_BLOCKS
#define ST_BUFFER_BLOCKS 32                                /* 安全兜底 */
#endif
```

上游默认值刻意指向"从内核源码取缓冲块数"，在 CI/交叉环境必然
`fatal error: '/usr/src/linux/…' file not found`。
**正确做法是刻意不定义该宏** —— 源码紧接着的 `#ifndef … #define 32` 会兜底，
且 Makefile 注释自陈 *"The value of the kernel is normally ST_BUFFER_BLOCKS=32"*，
说明 32 就是上游认可的取值。

### 坑 3：`OBJ` 跨续行，漏成员只在**链接期**暴露

只读到第一行会漏掉 `zf-cre-open.o`（提供 `reopen/creopen/zfopen/cclose`）与
`dds_chkhdr.o`（提供 `dds_is_tar_header_record`），编译全部通过、**链接才报**
`undefined symbol`。这两个恰好是"次要功能"模块（零填充直读、tar 头校验），最容易被忽略。

## 可复用做法：动手前做「Makefile 契约核对」三件事

```bash
# ① 完整展开跨续行变量（OBJ / CCFLAGS / CCOPT …）
awk '/^OBJ=/{f=1} f{print; if($0 !~ /\\$/) exit}' Makefile
# ② 枚举全部命令行宏
grep -nE '^\s*[A-Z_]+\s*=-?D' Makefile
# ③ 对"触发宿主机绝对路径"的宏做反向判断：某个取值会让源码 include 宿主机路径，
#    就不要注入该值，改用源码兜底或上游注释认可的值
grep -rn '/usr/\|/usr/local\|/opt/' *.h *.c | head
```

然后逐宏判定：**源码是否依赖它？依赖则必须注入；不注入也要显式确认有兜底。**

## 边界与查重

- **E392**（Raw makefile Conan 配方的三个通用陷阱：BadZipFile 编码器误选 /
  compiler_executables 字典获取 / make 默认 cwd 错误）：那条讲的是"**调用 make
  本身**"的三个陷阱；本条讲的是"**绕过 make 直编**"时与 Makefile 的**契约不等价**，
  症状集合（语法错误 / 宿主机头 / 链接符号）与处置方式均不同，**不合并**。
- **E483 / E276**（`get()` 对无扩展名 URL 报 BadZipFile）：属取源阶段，与本条无关。
- 正式库以 `st_options.h` / `CCFLAGS` / `undefined symbol: zfopen` 等检索无命中。

## 关联

- 配方 PR：**!9363**（dds2tar 2.5.2 适配 HarmonyOS PC，分支 `feat/dds2tar-2.5.2`）
- 平台任务：#7026（dds2tar 2.5.2）
- 本 Issue 与 PR 双向关联；草稿经主编审核后由 promote 流程转入正式知识库。
