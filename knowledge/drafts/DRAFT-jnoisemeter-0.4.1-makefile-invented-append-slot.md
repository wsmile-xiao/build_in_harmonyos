# DRAFT: 裸 Makefile 没有可追加的 include 槽位时，自造一个"只被引用、从未被赋值"的变量当注入通道

> Contributor: 主理-64 | Status: DRAFT | Created: 2026-09-26
> 来源: jnoisemeter 0.4.1 适配（`source/Makefile` 全文 52 行，只有
> `jnoisemeter` / `install` / `uninstall` / `clean` 四个目标）

## 症状

jnoisemeter 上游是一份裸 Makefile，依赖头文件路径完全靠宿主探测（原文第 26 行）：

```make
VERSION = 0.4.1
CPPFLAGS += -MMD -MP -DVERSION=\"$(VERSION)\"     # 25 行
CPPFLAGS += $(shell pkgconf --cflags freetype2)   # 26 行 ← 宿主 pkgconf
CXXFLAGS += -O2 -Wall                             # 27 行
```

OHOS 交叉构建时这条 `pkgconf --cflags freetype2` 探的是构建机的宿主 pkg-config，
FreeType/Xft 的头其实在 Conan 包里，编译期直接报头文件找不到（`ft2build.h`、
`Xft/Xft.h` 一类）。而这份 Makefile **没有任何"独立且可追加"的 include 变量**：
`CPPFLAGS` 只被 `+=` 用，没有 `AM_CPPFLAGS`/`INCFLAGS` 那样的分层落点。

直觉解法是命令行传 `CPPFLAGS`。它会在下一步炸得更隐蔽：

```
# 覆盖 CPPFLAGS 之后，上游自己的宏没了 —— 而 VERSION 是被源码当真用着的
jnoisemeter.cc:50:    fprintf (stderr, "\n%s-%s\n\n", PROGNAME, VERSION);
mainwin.cc:55:        sprintf (s, "%s - %s  [%s]", PROGNAME, VERSION, jclient->jname ());
```

## 判据（两问，`make -n` 就够，不必真编译）

```sh
# 1) 候选变量是不是"只被引用、从未被赋值"？
grep -n  'PCONFCFL' Makefile                       # 只应有引用行
grep -nE '^[ 	]*PCONFCFL[ 	]*[:?+]?=' Makefile     # 必须空（rc=1）

# 2) 实测覆盖 CPPFLAGS 会不会吃掉上游的 +=
make -n jnoisemeter CPPFLAGS=-DX | head -1
make -n jnoisemeter PCONFCFL=-DX | head -1
```

## 实测读数（jnoisemeter 0.4.1，2026-09-26，同一份 Makefile 同一份源码）

补丁后 `source/Makefile:26` 是 `CPPFLAGS += $(PCONFCFL)`，全文件 `PCONFCFL`
仅此一次出现、且从未被赋值（`grep -nE '^[ \t]*PCONFCFL[ \t]*[:?+]?='` → rc=1）。

```
$ make -n jnoisemeter
clang++ --target=aarch64-linux-ohos -O2 -Wall -MMD -MP -DVERSION=\"0.4.1\"   -c -o jnoisemeter.o jnoisemeter.cc

$ make -n jnoisemeter CPPFLAGS=-DDUMMYWIN
clang++ --target=aarch64-linux-ohos -O2 -Wall -DDUMMYWIN  -c -o jnoisemeter.o jnoisemeter.cc
#                                                            ↑ -MMD -MP -DVERSION 三项全没了

$ make -n jnoisemeter PCONFCFL=-Ifake/inc
clang++ --target=aarch64-linux-ohos -O2 -Wall -MMD -MP -DVERSION=\"0.4.1\" -Ifake/inc  -c -o jnoisemeter.o jnoisemeter.cc
#                                                            ↑ 上游 += 保留，注入项追加在末尾
```

口径说明：本稿实测到的是"上游 flag 从编译命令行消失"这一层；没有另外构造一次
去掉 `-DVERSION` 的真编译去取第一条报错原文（按上面的两处引用点，下场是
undeclared identifier，属可推断而本稿未实测的部分）。

## 根因

GNU make 的变量优先级里**命令行赋值高于 makefile 内赋值，而且是整体替换**：
一旦命令行给了 `CPPFLAGS=...`，makefile 里的 `CPPFLAGS += ...` 就不再参与，
上游塞的 `-MMD -MP -DVERSION=\"$(VERSION)\"` 连带消失（上面第二行读数）。
反过来，命令行赋一个 makefile 里**只被引用、从未被赋值**的变量，命中的是
`$(PCONFCFL)` 这个空位，`CPPFLAGS +=` 的累加链路一点没被碰。

## 修法

补丁只改一行右值，把槽位造出来：

```diff
-CPPFLAGS += $(shell pkgconf --cflags freetype2)
+CPPFLAGS += $(PCONFCFL)
```

配方侧照 `conanfile.py:112-116` 原文传值：

```python
self.run('make -C "{}" -j1 CXX="{}" PCONFCFL="{}" LDFLAGS="{}" jnoisemeter'
         .format(source_dir, cxx, pconfcfl, ldflags))
```

`pconfcfl` 由 `conanfile.py:92-106` 拼出：OHOS 时先加 `-DCLTHREADS_NO_PTHREAD_CANCEL`，
再遍历 `self.dependencies` 对每个 `includedirs` 追加 `-I`；`ldflags` 同理收 `libdirs`。
落到命令行形如：

```
make -C source -j1 CXX=.../clang++ \
     PCONFCFL=" -DCLTHREADS_NO_PTHREAD_CANCEL -I.../clxclient/3.9.2/include -I.../clthreads/2.4.0/include ..." \
     LDFLAGS=" -L.../clxclient/3.9.2/lib -L.../jack/1.9.22/lib ..." jnoisemeter
```

变量名沿用同族已合并配方（clxclient 3.9.2、aliki 0.3.0 的上游 Makefile（⚠ aliki 实为该补丁加行造出的槽位，非上游自带，见其 patches/0001:14 与 notes.md:33 才自带；aliki 的上游则没有
`PCONFCFL` 槽位）；**名字不是知识，"只引用不赋值"这个形状才是**。

## 适用边界与反例

* 只对"从未被赋值"的变量成立。上游若已有 `FOO = ...`，命令行覆盖它同样会整体
  换掉上游的值 ⇒ 得先证明覆盖等价，否则回到"补丁改右值"。
* 上游把编译 flag 放在 `CXXFLAGS`/`CFLAGS` 的包，造出的槽位要落在编译命令真正
  引用的那个变量上，否则注入了也不生效。
* 反例：Makefile 已提供 `CPPFLAGS ?=` 或独立 `INCFLAGS` ⇒ 那是正常追加点，
  不需要造槽位，本条不适用。
* 本条只管编译期 include 路径，不解决"链接行没有 `-L`/`-l` 注入点"（那是
  `DRAFT-zerofree-1.1.1-makefile-linkline-flags-and-musl-transitive-include`
  的范围）；本包链接行本就引用 `$(LDFLAGS)`，命令行直接赋值即可。

## 与既有条目的边界 / 查重

四范围（`knowledge/graph/`、`knowledge/drafts/`、`经验文档/B草稿库/`、
`经验文档/手册/07-技术速查.md`）以 "PCONFCFL"、"pkgconf --cflags"、
"从未被赋值的变量" 等关键词检索，**2026-09-26 全部 0 命中**。

* `DRAFT-zerofree-1.1.1-makefile-linkline-flags-and-musl-transitive-include`：
  处理的是"链接行只带 `$(CFLAGS)`、没有 `-I/-L` 位置"，修法是**把上游链接行改成
  接受标准变量**（动的是 Makefile 里的 recipe）。本条恰恰是**不动 recipe**，
  而是在 makefile 变量拓扑里造一个空位，从命令行注入；两者可叠加但机制不同。
* `E466`（`knowledge/graph/E466.kv:22,36`，init-build 的嵌套源码提升）、
  `E478`（`knowledge/graph/E478.kv:22,34,36`，conan-verify 点号版本号导致
  G4/L2/L4/L5 跳过）：本包都命中了，但都是框架侧症状，与本条源码机制无关。
* `DRAFT-8958-clthreads-makefile-stage-install-shadow.kv:92,98`
  （`forbid_2`：裸 `install` → `INSTALL=/bin/install`；`forbid_3`：
  `CXXFLAGS += -march=native`）：本包补丁的另两处沿用其判据，属"取用"，不属本条新增。
* 同族已合并配方 `archives/c/clxclient/3.9.2`、`archives/a/aliki/0.3.0` 的代码里
  出现过 `PCONFCFL` 这个用法，但那是上游自带槽位的直接复用，知识库里没有
  "上游没槽位时如何造一个" 的判据 —— 这正是本条的新增价值。

## 上游测试情况

上游零测试：`source/Makefile` 只有 `jnoisemeter` / `install` / `uninstall` / `clean`
四个目标（第 35/41/46/50 行），`cd source && make check` 原文
`make: *** No rule to make target 'check'.  Stop.`，tarball 内无 `tests/`。
适配后的验证来自配方自带的 `test_package`（2 例 / 3 断言真跑并 PASS），
以及 W3 本地 CI 模拟里 `L1_RESULT=pass: test_package executed`、
`L1e: Negative test confirmed — test genuinely depends on jnoisemeter`
（`L2_RESULT=skip: jnoisemeter version/help failed` 上游无 `--version`/`--help`，
按 skip 如实记录，不计通过）。
