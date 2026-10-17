# 两个"不要引入的不必要依赖"：代码生成器，与私有符号

> Draft: DRAFT-nedit-5.8-generated-source-and-private-motif-symbol
> Stem: `nedit-5.8-generated-source-and-private-motif-symbol` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-nedit-5.8-generated-source-and-private-motif-symbol
- **严重度**: 2
- **类别**: build-system|generated-source|linking|private-abi|motif|portability
- **触发工具**: make|clang|conan|linker
- **阶段**: configuration|compilation|linking

## 错误特征

两条独立的坑，报错形态完全不同：

```
# 坑一：生成器不在 worker 上（上游有回退，所以不一定真失败）
bison -o parse.c parse.y || ( yacc parse.y && mv y.tab.c parse.c ) || \
        cp parse_noyacc.c parse.c
make[1]: bison: No such file or directory
make[1]: yacc: No such file or directory
```

```
# 坑二：私有符号解析不到（这一条一定会失败）
help.o: in function `getBuildInfo':
help.c:(.text+0x...): undefined reference to `_XmVersionString'
```

坑二的报错特别容易归错因：Motif 本身编得好好的、包也发布了，看起来像
"Motif 包不完整"或"库导出表有问题"，而真正的原因是**我们自己**多加了一个宏。

## 根因分析

### 坑一：生成文件 + 上游自带回退

`source/parse.c` 是由 `source/parse.y` 生成的，`source/Makefile.common` 给了
**三级**回退：

```make
parse.c: parse.y
	@echo "NOTE:  Don't worry about 'command not found' errors here"
	@echo "       unless you have changed the parse.y file."
	bison -o parse.c parse.y || ( yacc parse.y && mv y.tab.c parse.c ) || \
		cp parse_noyacc.c parse.c
```

上游的注释说得很直白：*"Don't worry about 'command not found' errors here"*——
它**预期**很多机器上两个生成器都没有，因此随包带了一份 checked-in 的
`parse_noyacc.c` 作为回退。

既然回退是官方的，最干净的做法就是**预拷贝**它，让构建根本不需要走这条规则：

```python
shutil.copyfile(os.path.join(src, "source", "parse_noyacc.c"),
                os.path.join(src, "source", "parse.c"))
```

一个小而关键的细节：`copyfile` 把 `parse.c` 的 mtime 设成**当前时间**，而
`parse.y` 的 mtime 来自 tar 解压（2026-04）。于是 make 认为 `parse.c` 比它的
输入更新，规则不会重跑——正是我们想要的。反过来说，如果只是"删掉 parse.c 让
make 自己生成"，就会多一次必然失败的 `bison`/`yacc` 尝试（虽然最终也能成功，
但构建日志被污染，且换 worker 时行为可能不同）。

### 坑二：#ifdef 出来的"可选能力"，代价是非公开 ABI

`source/help.c` 里：

```c
#ifdef HAVE__XMVERSIONSTRING
extern char _XmVersionString[];
#else
static char _XmVersionString[] = "unknown";
#endif
```

这个字符串最终出现在 `nedit -V` 输出的 `Running Motif: %d.%d [%s]` 里。

- **不定义**：使用 help.c 自带的 `static char _XmVersionString[] = "unknown"`，
  输出 `Running Motif: 2.3 [unknown]`。零额外依赖。
- **定义**：链接期必须从 `libXm` 解析出 `_XmVersionString`。这是 Motif 的
  **私有**符号——名字以 `_Xm` 开头，不在任何公开头文件的承诺范围内，上游
  Motif 随时可以改名字或停止导出。

Debian 选择定义它，因为 Debian 的 nedit 要打印运行期 Motif 版本，且它面对的
是长期存在的发行版 libXm。这不是"上游要求"，而是"一个发行版的取舍"。

同样的判断也适用于 Debian 的另一个宏 `-DBUILD_UNTESTED_NEDIT`：它是给
"上游已知有问题的 Motif 版本"准备的逃生门。而本包依赖的 Motif 2.3.8 在这里
是**已知良好**的——`util/motif.c` 的自检逻辑写得很明确：

```c
else if (XmFullVersion >= 200203 && XmFullVersion <= 200308) /* 2.2.3 - 2.3.8 is good */
    result = MotifKnownGood;
```

`XmFullVersion` 对 2.3.8 是 `200308`，正好落在"good"区间。所以这个宏也不需要。

### 统一的判据

两条坑其实是同一条原则的两种形态：**不要因为"别处这么配"就引入一个不必要
的依赖**——无论那个依赖是一个代码生成器，还是一个私有链接符号。

| | 坑一 | 坑二 |
|---|---|---|
| 依赖对象 | bison / yacc（worker 上的工具） | `_XmVersionString`（libXm 私有符号） |
| 是否需要 | 上游已提供 checked-in 回退 → 不需要 | 目标平台无承诺 → 不定义 |
| 处置 | 预拷贝 `parse_noyacc.c` | 不加 `-DHAVE__XMVERSIONSTRING` |
| 如果不处置 | 多一次失败尝试 / 换 worker 抖动 | 链接失败，且报错指向 Motif |

**不定义是零风险的默认，定义才需要证据。** 证据形式是：目标平台上该符号确实
存在、已发布、并被认为是公开 ABI。发行版的 CFLAGS 在这里只能当线索。

## 解决方案

**主方案**: prefer-upstream-fallback-and-refuse-private-abi-flags

```python
# 规则一：生成文件用上游官方回退顶掉
shutil.copyfile(os.path.join(src, "source", "parse_noyacc.c"),
                os.path.join(src, "source", "parse.c"))

# 规则二：只保留上游平台 makefile 里的宏，发行版的取舍一律不抄
cflags += ["-DUSE_DIRENT", "-DUSE_LPR_PRINT_CMD"]
# 不加 -DHAVE__XMVERSIONSTRING，也不加 -DBUILD_UNTESTED_NEDIT
```

**备选**（仅当上游没有 checked-in 回退时）：给配方加
`tool_requires("bison/...")`，让 Conan 把生成器带上 worker。代价是生成结果随
工具版本漂移、可复现性下降。注意此时**不要**同时把生成产物提交进仓库。

## 验证

```sh
# 坑一：确认回退是官方提供的
grep -n 'parse\.c: parse\.y' -A3 source/Makefile.common
ls source/parse_noyacc.c

# 坑二：确认 #ifdef 的两个分支与 Debian 的取舍
grep -n 'HAVE__XMVERSIONSTRING' -B2 -A3 source/help.c
grep -n 'HAVE__XMVERSIONSTRING\|BUILD_UNTESTED_NEDIT' debian/rules
grep -n 'XmFullVersion' util/motif.c      # 确认 2.3.8 落在 good 区间

CI_PACKAGES="archives/n/nedit/5.8" zsh ci/conan/build_and_test.sh
# 构建日志中不应出现 bison / yacc 的查找；链接不应引用 _XmVersionString
```

## 关联条目

- 同批条目 `DRAFT-nedit-5.8-use-dirent-musl-vs-distro-cflags`：那条的结论是
  **必须定义** `USE_DIRENT`（因为目标平台缺少 `<sys/dir.h>`），本条的结论是
  **不要定义** `HAVE__XMVERSIONSTRING`（因为会把私有 ABI 拉进来）。两条合起来
  就是"宏该不该定义"的完整判据：**看目标平台缺什么，与看要不要私有 ABI**。
- 与 `DRAFT-nedit-5.8-handwritten-makefile-dispatcher-and-dev-targets` 相接：
  那条决定了"构建期不执行产物"，本条的坑一决定了"parse.c 由谁产出"——两者
  共同构成这个手写 makefile 项目在 Conan 里的可复现构建路径。
