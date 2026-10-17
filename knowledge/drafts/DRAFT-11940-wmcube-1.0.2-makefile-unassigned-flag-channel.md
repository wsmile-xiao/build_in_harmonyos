# 裸 Makefile 的依赖注入通道判别：未赋值变量走环境，已赋值变量只能命令行整串接管

> Contributor: 主理-64 | Status: Draft（路径 B 候选，未 promote）| Updated: 2026-09-26
> 结构键见同目录 `DRAFT-11940-wmcube-1.0.2-makefile-unassigned-flag-channel.kv`。

## 症状

把一个"没有 configure、直接 `make`"的上游包搬进 Conan 时，依赖的 `-I/-L` 注入有三种表现，
而三者的差别只取决于一个此前没人写的判别式：

> **取证口径（r2 整改）**：下面这个代码块是本条**唯一的一手症状读数**，取自随 PR 的
> `archives/w/wmcube/1.0.2/reports/conan-create.log:163-166` 与 `:175`（L1 harness 自己解析
> 产物 `.dynamic` 后的输出）。旧稿在此以带出处的形态写过 `wmcube.c:12:10: fatal error: ...
> shape.h file not found` 与 `ld.lld: error: unable to find library -lXext` 两行报错原文——
> **它们不是一手读数，本包从未触发**：本轮对 `~/tmp/uc2/z64-wmcube/*.log`、`logs/*.log`、
> `w0/*.log`、`evidence/*.log`、`STATE.md` 以及本包 `reports/` 下两件日志逐件 grep
> `file not found` / `unable to find library` / `cannot find -l`，**全部 0 命中**，两行已删。

```console
       DT_NEEDED[1] = libXext.so.6
       DT_NEEDED[2] = libXpm.so.4
       DT_NEEDED[3] = libX11.so.6
RESULT: PASS (16/16 assertions passed, 0 failed)
```

三种变量形态各自对应的症状（**前两档本包未观测，只列形态**；第三档才是本包真正规避掉的
风险，一手依据是 `archives/w/wmcube/1.0.2/conanfile.py` 里 `build()` 的 make 命令行
（`make -j1 CC=... LIBDIR= INCDIR=`）中根本没有 `CFLAGS`）：

| 变量形态 | 注入出错时的表征 | 本包是否观测 |
|---|---|---|
| 使用但未赋值的 `CPPFLAGS` 没接上环境 | 编译期依赖头找不到（`... file not found` 一类） | **否**（0 命中，见上） |
| 使用但未赋值的 `LDFLAGS` 没接上环境，或 `-l` 排在所有 `-L` 之前 | 链接期依赖库找不到（`cannot find -l` / `unable to find library` 一类） | **否**（0 命中，见上） |
| 已被赋值的 `CFLAGS` 被命令行整串接管 | 上游 `-Wall -O2` **静默**消失，无任何报错 | 规避（见上命令行） |

## 根因与判别式

手写 makefile 把检索路径写成变量再在规则里展开。make 的取值优先级是
**命令行变量 > makefile 内赋值 > 环境变量**，于是同一个 makefile 里的两类变量需要两种截然不同的注入法：

| 变量形态 | 环境能否注入 | 正确做法 |
|---|---|---|
| **使用但从未赋值**（典型 `CPPFLAGS`、`LDFLAGS`） | 能 | 什么都不写，让 `conanbuild` 环境的值直接生效 |
| **已被赋值**（典型 `CC`、`CFLAGS`、`LIBDIR`、`INCDIR`、`LIBS`） | 不能（被 makefile 赋值覆盖） | 只能上命令行，且命令行是**整串替换**，必须把要保留的原值一起给 |

判别命令（一次读数即可分类，零成本）：

```sh
grep -nE '^[[:space:]]*(CPPFLAGS|LDFLAGS|CFLAGS|CXXFLAGS|LIBS|LIBDIR|INCDIR|CC)[[:space:]]*[:+?]?=' Makefile
```

## 最小接管方案（本次实测通过）

wmcube 的 `wmcube/Makefile` 只有 6 行赋值，恰好留下 `CPPFLAGS`/`LDFLAGS` 两条自由通道：

```make
.c.o:
	$(CC) $(OS) $(CPPFLAGS) $(CFLAGS) $(INCDIR) -c $< -o $*.o
wmcube: $(OBJS)
	$(CC) $(LDFLAGS) -o wmcube $^ -lXext $(LIBDIR) $(LIBS)
```

```python
self.run(f'make -j1 CC="{cc}" LIBDIR= INCDIR=', env="conanbuild", cwd=...)
```

三条要点：

1. **只接管必须改的**：`CC`（上游烧 `gcc`）、`LIBDIR=`/`INCDIR=`（清掉 `-L/usr/X11R6/lib`、
   `-I/usr/X11R6/share/include` 两条死路径）。
2. **`CFLAGS` 刻意不接管** —— 接管即整串替换，会静默丢掉上游的 `-Wall -O2`（正式记录见 `knowledge/graph/E465.kv:27`：「Only a make command-line variable overrides the assignment」；旧稿作「同族教训 E568」系误引——`knowledge/graph/E568.kv` 不存在）。
3. **`-L` 顺序坑顺带解决**：链接行里 `-lXext` 写在 `$(LIBDIR)` 之前，若按常规只接管 `LIBDIR`，
   `-lXext` 仍会在所有 `-L` 之前被处理而找不到库；走 `LDFLAGS` 这条环境通道时
   `$(LDFLAGS)` 展开在最前，`-L` 天然排在 `-lXext` 前面。

## 禁手

- **只写自己那一份优化档去接管 `CFLAGS`** ⇒ 上游告警/优化被静默清除，产物与社区构建不一致且无人报错。
- **把 `-/usr/local` 等系统前缀写进配方** ⇒ 依赖构建机现装环境、不可复现并污染系统目录（R49/E524）。

## 适用边界（务必先分层，别与既有机制混判）

- 适用：无 configure/automake 的裸 makefile，且目标变量确实未被赋值。
- **不适用**：automake 的 per-target `*_CPPFLAGS =`（空赋值）+ VPATH 场景——那里变量**已被（空）赋值**，
  环境进不去，必须把 `-I` 逐个回填到命令行，见
  `knowledge/drafts/DRAFT-10251-libnfc-tools-1.8.0-automake-per-target-cppflags-empty-override.kv`
  （其 `error_signature`/`prescan_pattern` 在本条对象里一条都不出现，二者是同一根轴的两端，不可互替）。
- 与"make 命令行变量是接管而非追加"（正式记录见 `knowledge/graph/E465.kv:27`；旧稿误作「E568 同族」，该号在 `knowledge/graph/` 无条目、`knowledge/graph/index.tsv` 首列零命中，只是 `knowledge/drafts/` 下被复用的文件名前缀）不冲突：那条讲**接管时要给全**，本条讲**哪些变量根本不该接管**。

## 验证证据（wmcube 1.0.2，B 机构建主机）

```console
$ make -j1 CC=/data/service/hnp/bin/clang LIBDIR= INCDIR=          # env=conanbuild
（一次通过，无 cannot find -l / 无 file not found）

# DT_NEEDED 由本包 test_package/test.c 自行解析产物 .dynamic 段得到
# （未使用 readelf/objdump——那类工具在 worker 上是否可得未验证），
# 原文见 archives/w/wmcube/1.0.2/reports/conan-create.log:163-166：
       DT_NEEDED[1] = libXext.so.6
       DT_NEEDED[2] = libXpm.so.4
       DT_NEEDED[3] = libX11.so.6
       DT_NEEDED[4] = libc.so
  [PASS] A10 linked against libX11 (upstream -lX11)
  [PASS] A11 linked against libXext (XShapeCombineMask)
  [PASS] A12 linked against libXpm (XpmCreatePixmapFromData)

$ conan-verify wmcube 1.0.2  →  VERIFY_RC=0，报告 **Verdict**: PASS
   G0/G1/G2/G3/G4/L2/L4/L5 全 PASS；L1 harness: RESULT: PASS (16/16 assertions passed, 0 failed)
```

上游测试面为 **0**（`make -n check` → `make: *** No rule to make target 'check'.  Stop.` rc=2），
故本条不声称任何上游测试通过数。
