# DRAFT-lisgd-0.3.7-suckless-baked-paths-makevar-override

> suckless 裸 Makefile 烧死 `CC=cc` 与 `X11INC/X11LIB=/usr/X11R6/*` 系统路径，
> 且上游用 **`+=` 内联引用**这两个路径变量 ⇒ 在 make 命令行**覆盖路径变量本身**
> （另用无 `+=` 的 `CFLAGS`/`LDFLAGS` 携带其余依赖 -I/-L），注入 Conan 依赖目录、**零补丁**。
> ⛔ **覆盖聚合变量 `CPPFLAGS`/`LIBS` 会把 `+=` 追加整段吞掉，双后端静默缺失**。
>
> 配套 kv：`knowledge/drafts/DRAFT-lisgd-0.3.7-suckless-baked-paths-makevar-override.kv`
> 机制源自 B 草稿库通用池件 `DRAFT-PKG-VER-suckless-baked-paths-makevar-override`（M18），
> 本条是该池件 `safety_boundary` ② 所指分支的**首例实物**。

## 上游实物（lisgd 0.3.7 裸 Makefile，全文 49 行）

```make
PREFIX = /usr
SRC = lisgd.c          LDFLAGS = -g              LIBS = -linput -lm
X11INC = /usr/X11R6/include
X11LIB = /usr/X11R6/lib

ifndef WITHOUT_X11
CPPFLAGS += -I${X11INC} -DWITH_X11          # ← 聚合变量累加，内联引用 X11INC
LIBS     += -L${X11LIB} -lX11               # ← 同上，内联引用 X11LIB
endif
ifndef WITHOUT_WAYLAND
CPPFLAGS += -DWITH_WAYLAND
LIBS     += -lwayland-client
endif

.c.o: ${CC} -c ${CFLAGS} ${CPPFLAGS} $<     # CFLAGS 上游为空、无 +=
lisgd: ${OBJ}  ${CC} -o $@ ${OBJ} ${LDFLAGS} ${LIBS}
```

## 症状（两层，lisgd 0.3.7 实测 2026-10-03 B 机）

```
$ make
cc -c  -I/usr/X11R6/include -DWITH_X11 -DWITH_WAYLAND lisgd.c
make: cc: No such file or directory          # 第一层：CC 烧死/隐含 cc，OHOS 无 cc 别名
make: *** [Makefile:31: lisgd.o] Error 127

$ make CC=/data/service/hnp/bin/clang
lisgd.c:3:10: fatal error: 'libinput.h' file not found   # 第二层：交叉环境无系统头
        #include <libinput.h>
```

> 注：本包的第二层头错误先落在 `libinput.h`（源文件 L3 就 include）而不是 `X11/Xlib.h`，
> 因为 `X11/Xlib.h` 在源文件 L14 的 `#ifdef WITH_X11` 里、顺序在后。

## 修法（零补丁）

```sh
make CC=<conf tools.build:compiler_executables 取得> \
     CFLAGS='-O2 -I<全部 host 依赖的 -I>' \
     X11INC=<libx11 package>/include \
     X11LIB=<libx11 package>/lib \
     LDFLAGS='<全部 host 依赖的 -L>' -j1
```

- **覆盖 `X11INC`/`X11LIB`（路径变量）** ⇒ 上游两条 `+=` 自动把
  `-I${X11INC}` 与 `-L${X11LIB} -lX11` 展开到依赖目录；
- **覆盖 `CFLAGS`/`LDFLAGS`（上游无 `+=` 引用）** ⇒ 安全携带 libinput / eudev /
  wayland / xorgproto 等其余依赖路径；
- **`CPPFLAGS`/`LIBS` 一律不覆盖**；
- 编译器走 conf（R33），缺键即 `ConanInvalidConfiguration`，不硬编码 clang；
- 依赖路径用 `self.dependencies.host` **传递聚合**（`libinput.h:35` 要 `<libudev.h>`、
  `X11/X.h` 要 xorgproto，两者都是传递依赖）；
- 上游源码零改动、`patches: {}`。

### 修后读数

```
$ make CC=... CFLAGS=... X11INC=... X11LIB=... LDFLAGS=... -j1     # P3_RC=0
clang -c -O2 -I<依赖…> -I<libx11>/include -DWITH_X11 -DWITH_WAYLAND lisgd.c
clang -o lisgd lisgd.o -L<依赖…> -linput -lm -L<libx11>/lib -lX11 -lwayland-client
$ llvm-readelf -d lisgd | grep NEEDED
  libinput.so.10  libX11.so.6  libwayland-client.so.0  libc.so
$ make install PREFIX=<package_folder> ...                          # INSTALL_RC=0
  usr/bin/lisgd          usr/share/man/man1/lisgd.1
```

## ⛔ 关键边界：覆盖错层是**静默失败**（P4/P5 反证）

```
$ make -n CC=<clang> CFLAGS='…' CPPFLAGS='-I<libx11>/include'
echo "CPPFLAGS = -I<libx11>/include"          # ← 只剩覆盖值
clang -c … lisgd.c                            # -DWITH_X11 与 -I${X11INC} **消失**，无报错

$ make -n … LIBS='-linput -lm'
echo "LIBS     = -linput -lm"                 # ← -L${X11LIB} -lX11 -lwayland-client **消失**，无报错
```

编译仍会"成功"（`-DWITH_X11` 只是让 X11 分支不编），**交付的二进制缺一个显示后端**
—— 这正是为什么必须先读 Makefile 判断聚合变量是 `=` 还是 `+=`：

| 上游形态 | 正确覆盖对象 | 实例 |
|---|---|---|
| 聚合变量 `INCS = ...`（`=`，不累加） | **聚合变量** | dmenu 5.4 config.mk（M18 池件原文） |
| 聚合变量 `CPPFLAGS += <引用路径变量>`（`+=` 累加） | **路径变量** + 无 `+=` 的 CFLAGS/LDFLAGS | **lisgd 0.3.7（本条）** |

## 退路：上游自带双后端开关（P6 实测有效）

```sh
$ make -n WITHOUT_X11=1 CC=<clang>
echo "CPPFLAGS = -DWITH_WAYLAND"
echo "LIBS     = -linput -lm -lwayland-client"
```

`ifndef WITHOUT_X11` / `ifndef WITHOUT_WAYLAND` 是 suckless 的标准做法 ⇒ X11 面撞能力墙
（如 libx11 生态版本系冲突无法组图）时可**退纯 Wayland 后端**，优先于打补丁或转手。

## 判别与边界

- 只适用**裸 Makefile / config.mk** 且路径烧死的包；autotools、CMake 不适用。
- 与 M13（`DRAFT-lzip-1.24.1-makefile-install-cmd-absent-makevar-override`）
  同为 make 命令行变量覆盖，但那条症状在 `package()` 的 install 命令缺失、
  解法是替换安装工具语义；本条在 `build()` 的编译/链接路径注入，不重叠。
- 与 E386/E540（autoconf 生成物的 configure 路由/宿主探测）不同构建族。
- 运行期能力墙：OHOS 上 `/dev/input` 无节点且 Permission denied、
  `DISPLAY`/`WAYLAND_DISPLAY` 均空 ⇒ 本族守护进程**无法验真实手势触发**，
  验证只到参数层 + 显示探测层 + 运行期动态加载零错误；**不可据此把构建判失败**。
- 依赖 `.so` 签名面：本包依赖图内 74 个 `.so` 全带 `.codesign`，B 机设
  `LD_LIBRARY_PATH` 后全部可加载 ⇒ 未复现 dmenu #12032 的跨机拒载，本包不加重签 stage。

## `draft-review` 实测（2026-10-03，工具 rc=0，逐字）

```
质量预检: signature=✅  root_cause=✅  rec=✅
相似正式条目 TOP3:
  E169  score=0.44  (sig=0.8 kw=0.0 cat=0.0)
  E217  score=0.37  (sig=0.67 kw=0.0 cat=0.0)
  E174  score=0.21  (sig=0.38 kw=0.0 cat=0.0)
📌 预审建议: review-similar → E169   灰区——需人工判断与目标条目的关联性
```

- 三态判据是 `score >= _MERGE_TH(0.55)`，**0.44 未触及 merge-into 阈值**；
  工具原文明示「以上建议仅为相似度计算参考；是否纳入正式知识库由人工审核决定」。
- 人工比对：**E169** = 系统缺 GNU `argp.h`（平台缺件族）、**E217** = CMake
  `install(FILES …)` 落点族、**E174** = 缺 GNU `install` 命令（M13 族）。
  三者的 `kw` / `cat` / `phase` 维度得分**全为 0**，分数 0.44 / 0.37 / 0.21 全部低于
  `_MERGE_TH=0.55`。**共享的只是通用错误文案，不是同一机制** —— 而且三者并不共享同一句：
  E169 / E217 的共享签名片段是 `fatal` / `error:` / `found` 一类（`file not found`）；
  **E174 的共享片段是 `directory` / `found` / `make:`**（来自
  `make: install: No such file or directory` 与 `command not found`），
  其 `error_signature` 中**并无** `file not found`。
  （此点按 W4 独立复算更正：原文「重叠只来自 `file not found` 公共文案」对 E174 不精确。）
  本条的新增价值 = 「`+=` 内联引用形态下覆盖错层会**静默丢后端**」，
  M18 池件对此只有注意事项、无正反探针，本包以 P3/P4/P5/P6 四臂补齐。
- 复核命令：`python3 scripts/ohc-run.py draft-review DRAFT-lisgd-0.3.7-suckless-baked-paths-makevar-override`

