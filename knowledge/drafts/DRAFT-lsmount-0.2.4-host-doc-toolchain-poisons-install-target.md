# DRAFT-lsmount-0.2.4-host-doc-toolchain-poisons-install-target

> 裸 Makefile 的 `install:` 目标把「安装」与「宿主文档生成器 `a2x`」绑在同一条依赖链上，且全文件
> 没有 `PREFIX`/`DESTDIR`/`INSTALL` 任何一个可覆盖把手 ⇒ OHOS 交叉环境整条 install 不可用。
> 零补丁路线：`build()` 只跑 `make` 取二进制，`package()` 自行放置产物，不走上游 install 目标。
> 宿主证据 = lsmount 0.2.4（平台任务 8576，A 机鸿蒙 PC 实测）。

## 症状（源码静态证据，逐行可复算）

源包 `lsmount-0.2.4/Makefile`（48 行；取自已核 sha256 的官方 tag v0.2.4 归档）：

```make
3:  CC          = /usr/bin/gcc                 # simple 赋值：宿主编译器绝对路径被烧死
8:  LDFLAGS     = -ltermcap -z now             # simple 赋值：env 注入无效，只能命令行整体覆盖
13: all: CFLAGS += -O2 -Wall -pedantic -fPIE -D_FORTIFY_SOURCE=1
16: debug: CFLAGS += ... -Werror -Wextra ...   # -Werror 只在 debug 目标，all 路径不触发
36: install: lsmount manpage                   # install 依赖 manpage
37: 	 cp lsmount /usr/bin/$(BIN)             # 烧死 /usr/bin
38: 	 cp share/lsmount.rc.default /etc/lsmountrc   # 烧死 /etc
39: 	 cp doc/lsmount.1.gz /usr/share/man/man1/     # 烧死 /usr/share/man
46: manpage: doc/lsmount.txt
47: 	 a2x -f manpage doc/lsmount.txt         # 宿主文档生成器，交叉环境不可得
48: 	 gzip -f doc/lsmount.1
```

设备侧宿主工具实测（A 机，`which` 逐条）：`a2x` / `xmlto` / `install` / `cc` 均 **MISSING**；
`clang` 与 `make` 在 `/data/service/hnp/bin/`；`pkg-config` 存在（故 libconfig 的 `-I/-L` 由
`PKG_CONFIG` 提供，**不需要** INCS/LIBS 类聚合变量覆盖）。

复算命令（任何人可重跑，输出逐行带行号）：`grep -n '' Makefile`。

## 根因

上游把两件本来正交的事绑死在一起：①`install:` 的前置依赖是 `manpage:`，而 `manpage:` 要跑
`a2x`（asciidoc 家族，宿主文档生成器）；②安装目标是三条硬编码绝对路径，且**没有任何可覆盖把手**
（`BIN` 只是文件名，不是前缀）。于是交叉/沙箱环境里既补不齐文档工具链（装 `asciidoc` 属引入宿主工具，
且 CI 无该环境），又不能只跑"安装"那一半 —— 整条 `install` 目标是**结构性不可用**，而不是某一步报错可修。

关键鉴别（实测层次）：**首错在编译层（`CC` 被烧成 `/usr/bin/gcc`），修好编译后必撞文档层
（`a2x` 不存在），再往后才是写 `/usr/bin`、`/etc` 失败**。三层里只有第二层是本条目新增的机制面；
且**只覆盖 `CC` 并不足以编出来**（`make CC=<clang>` 仍报 4 errors，缺 conan 注入的
`PKG_CONFIG_PATH`）⇒ 编译必须走 conan 依赖环境，而安装要**整条绕开** `install` 目标。

## 最小复现（2026-09-25 A 机真机，读数原文）

层次必须分清：**编译层是首错，文档层是其后的独立卡点**。

① 编译层（烧死编译器绝对路径）：

```
$ make
/usr/bin/gcc -std=gnu99 -lconfig -D_GNU_SOURCE -fcommon `pkg-config --cflags libconfig` -O2 -Wall -pedantic -fPIE -D_FORTIFY_SOURCE=1 -c -o lsmount.o src/lsmount.c
Package libconfig was not found in the pkg-config search path.
/bin/sh: /usr/bin/gcc: inaccessible or not found
```

② 只覆盖 `CC` **不足以**编出来 —— 依赖路径必须一起由 conan 给：

```
$ make CC=/data/service/hnp/bin/clang
... 8 warnings and 4 errors generated.
make: *** [Makefile:22: lsmount.o] Error 1
$ # 在 conan 环境里（PKG_CONFIG_PATH 指向 libconfig 的 .pc）才编译链接成功
```

③ **文档层（本条知识的本体）**，单独隔离即复现，与 CC 无关：

```
$ make manpage
a2x -f manpage doc/lsmount.txt
make: a2x: No such file or directory
make: *** [Makefile:47: manpage] Error 127
$ command -v a2x        # 空 ⇒ 设备无该宿主工具
```

④ **install 目标无法只跑"安装"那一半**，`make -n install` 的展开里 a2x 与 gzip 必在：

```
$ make -n install | tail
/usr/bin/gcc ... -c -o helper.o src/helper.c
/usr/bin/gcc -o lsmount lsmount.o ... `pkg-config --libs libconfig` -ltermcap -z now
a2x -f manpage doc/lsmount.txt
gzip -f doc/lsmount.1
$ make install
/usr/bin/gcc ... -c -o lsmount.o src/lsmount.c
...
/bin/sh: /usr/bin/gcc: inaccessible or not found      # 首错在编译，修好后必撞 ③ 的 a2x，再往后是写 /usr/bin 与 /etc
```

⑤ **零把手的硬证据**（不是"没找到"，是全文件无命中）：

```
$ grep -n "PREFIX\|DESTDIR\|INSTALL" Makefile        # 无输出
```

## 已试过的失败方案

- `make PREFIX=<pkg 目录>` / `DESTDIR=<staging>`：⑤ 已证 `Makefile` 全文不引用这两个变量（行37-39 是字面绝对路径），传入无所作用。
- `make INSTALL=cp -f`：⑤ 同样证明上游没有 `INSTALL` 变量（行37-39 是裸 `cp`），无处下嘴。
- `make CC=<clang>` 想一步救活：② 实测仍 `4 errors`（缺 conan 给的 `PKG_CONFIG_PATH`）⇒ 必须走 conan 依赖环境，光覆盖 `CC` 不够。
- 保留 `install:` 只跳过文档：④ 的依赖展开在文件内写死，命令行只能选整个目标。
- 在设备上补装 `asciidoc`/`a2x`：属"为跑绿引入宿主工具链"，CI 侧无同环境，不可复现，弃。

## 最终方案（零补丁，上游源码与 Makefile 零改动）

- `build()`：只调 `make CC=<conf tools.build:compiler_executables 取得>`（必要时命令行整体覆盖
  `LDFLAGS`），产出 `lsmount` 二进制；**不**调上游 `install`。
- `package()`：由配方自行把 `lsmount` 放 `bindir`、`share/lsmount.rc.default` 放对应数据目录、
  `doc/lsmount.txt`（未经 a2x 的文档源）按需放 `resdir`，路径一律走 conan 给出的 package 前缀
  （同 E098 的 cp 路线，但**动机是文档依赖链毒化，不是 install 命令缺失**）。
- 不产 `.patch`、不改上游一行。

## 适用面（已验证 + 已排除）

- **已验证**：lsmount 0.2.4 —— 裸 Makefile、`install` 依赖宿主文档生成器、安装路径零把手。
- **同病人群**：任何默认目标链上挂着宿主文档生成器（`a2x`/`asciidoc`/`xmlto`/`ronn`/`sphinx`/`txt2man`）
  且安装路径硬编码的小包 —— 判据是 `grep -nE 'install:.*[^[:space:]]' Makefile` 看 install 的前置依赖里
  是否有非编译目标，再 `grep -n 'a2x\|asciidoc\|xmlto\|ronn\|sphinx-build\|txt2man' Makefile*`。
- **已排除（勿配，避免空走）**：
  - autotools / CMake 包（`configure`/toolchain 会重算前缀，`DESTDIR` 语义在）；
  - install 目标带 `PREFIX`/`DESTDIR`/`INSTALL` 把手的包 ⇒ 直接命令行覆盖，属 E098 / 通用池 M13 覆盖面；
  - 仅因 `-Werror` 挂掉的包 ⇒ 另一族（上游按 `host_os` 子串匹配开 -Werror 的那条见 xrdp 实证）。

## 查重与新增价值

对 `a2x`、`asciidoc`、`xmlto`、"文档目标毒化 install"在 适配经验汇总 / 经验库 / 适配检查清单 /
OHOS行为探针清单 / B草稿库 与仓库 `knowledge/` 目录全部命中 0 条。既有条目 E098（`install` 命令不可用
⇒ cp/chmod 自替）与 E108（补丁换 `ginstall`）症状签名同为 `install: command not found` 一类，
**未覆盖**本形态：不是 install 程序缺失，而是 install 的**依赖目标**需要宿主文档生成器、且无把手可绕。
新增价值 = 给出"绕开上游 install 目标"这一条判据与操作路径（先看 install 的前置依赖，再看有没有把手），
使后续同类包不再去补装宿主工具链或伪造 man 产物。

## 关联

- Issue：#3407（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3407）
- 平台任务：8576；分支：`feat/lsmount-0.2.4`；构建机：A 机鸿蒙 PC
- 运行期读数（本包 conan-verify / package 阶段原文行）：见同目录 `notes.md` 与 `reports/conan-verify-report.md`
