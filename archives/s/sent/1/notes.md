# 适配笔记 — sent 1

> 本轮（2026-09-23，主理-6 派下的起手轮）**只做起手与 W0 定性，未执行任何构建**：
> 没有跑 `conan create` / `conan-verify` / `finish` / `submit`，也没有跑 `init-build`
> 的编译步骤。下面凡是标注「未实测」的结论都只到静态分析为止，不得当成通过证据。

## 1. 上游与构建系统

- 源码：`https://dl.suckless.org/tools/sent-1.tar.gz`
  sha256 `7bf3de9311ce291ff36adf5315b78fa72373e3ab80ca71387fb5884bcbd7be33`
  （设备实测 HTTP 200 / 15285 B / gzip；`dl.suckless.org` 是 suckless 官方发布域，R39 合规）
- 构建系统：**裸 `Makefile` + `config.mk`**（suckless 家族惯例）。无 configure /
  autotools / CMake / meson。语言：C（`sent.c` `drw.c` `util.c` 三个 .c）。
- `config.mk` 里 `VERSION = 1`，与上游版本串完全一致，因此本包版本就是 `1`（R37：
  首次适配不加后缀；版本号与 `config.mk` 的 `VERSION` 也一致）。
- 源码文件构成：3 个 `.c` + 4 个 `.h`（`arg.h` `util.h` `drw.h` `config.def.h`）。

## 2. 归档布局是扁平的（踩点，别照抄 farbfeld）

`tar -tzf sent-1.tar.gz` 实测顶层直接是 `.gitignore LICENSE Makefile ... sent.c
util.h`，**没有 `sent-1/` 前缀目录**。

Conan 2.29.1 的 `untargz()`（`conan/tools/files/files.py`，`strip_root` 分支）对
扁平归档的第一个成员就会抛
`ConanException("Can't untar a tgz containing files in the root with strip_root enabled")`。
所以 `source()` 里**不能**传 `strip_root=True`。

对照：同族已合并的 `farbfeld/4.0` 就传了 `strip_root=True` 并且是对的——它的
`dist` 目标会 `mkdir -p farbfeld-$(VERSION)`，归档带顶层目录。
**结论：suckless 归档布局不统一，必须逐个 `tar -tzf` 实测，不能拿同族配方当模板抄。**
（sent 自己的 `dist` 目标也会建 `sent-${VERSION}` 目录，但**发布出来的** `sent-1.tar.gz`
是扁平的——这正是最容易看走眼的地方。）

⚠ 未实测：以上来自 conan 源码静态判读 + 真实 tar 包列表，`conan create` 阶段才会最终确证。

## 3. 依赖选型（W0）

上游 `config.mk` 的链接行：`LIBS = -L/usr/lib -lc -lm -L${X11LIB} -lXft -lfontconfig -lX11`。
直接链接三个库：**libXft、fontconfig、libX11**（`-lc` 由编译器驱动隐式链接，去掉）。
`sent.c` / `drw.c` 实际 include：`<X11/{keysym,XKBlib,Xatom,Xlib,Xutil}.h>`、
`<X11/Xft/Xft.h>`（`drw.c` 只用 `Xlib.h` + `Xft.h`）。

### libX11 选 1.8.13 而不是 6.4.0 —— 这是被约束逼出来的，不是偏好

本仓 X11 应用（xeyes 等）的已审口径是 `libx11/6.4.0 + libxext/6.4.0`（CI #28097 起
不再依赖预编译栈）。但 sent 必须链 `-lXft`，而：

- `archives/l/libXft/2.3.9/conanfile.py` 与 `2.3.8/conanfile.py` 都写死
  `self.requires("libx11/1.8.13")`（同时 `libxrender/0.9.12`、`fontconfig/2.18.3`、
  `freetype/2.14.3`、`xorgproto/2025.1`）。

⇒ 若 sent 直接 `requires("libx11/6.4.0")`，图中会出现 `libx11/1.8.13`（libxft 的硬 pin）
与 `libx11/6.4.0` 两个版本，是**版本冲突**，只能靠 `override=True` 强行改写上游 pin
才能过。那等于自己发明一套口径，并且要重验 libxft 是不是针对 1.8.13 编出来的。
**取 1.8.13 = 完全落在 libxft 自身已声明的闭包内，零冲突、零 override。**

选定的精确 ref（全部照抄 libxft/libx11 自己的 pin，不自创版本）：

| ref | 角色 |
|---|---|
| `libxft/2.3.9` | 链 `-lXft`，`<X11/Xft/Xft.h>` |
| `fontconfig/2.18.3` | 链 `-lfontconfig` |
| `libx11/1.8.13` | 链 `-lX11` |
| `libxrender/0.9.12` | 仅头文件（`Xft.h` 一侧需要）；与 libxft 的 pin 同版本 |
| `freetype/2.14.3` | 仅头文件；对应上游 `-I/usr/include/freetype2`；与 libxft 的 pin 同版本 |
| `xorgproto/2025.1` | 仅头文件（`X11/keysym.h` 等）；与 libx11/libxft 的 pin 同版本 |

后三个之所以**显式重列**（它们本来就在 libxft/libx11 的传递闭包里），是因为本配方要把
依赖的 `include/` 目录算进 `INCS`，而 conan 的 `self.dependencies` 只暴露**直接**依赖；
重列的版本与上游 pin **逐字相同**，故不可能引发冲突。

**这条"谁提供哪个头文件"的对应关系已实测，不是推断。** 用
`conan install --requires=... --build=never -pr:h=ci/conan/profiles/ohos-aarch64`
把 OHOS 二进制拉到本地缓存后逐个查（2026-09-23）：

| 头文件 | 实际由谁提供 |
|---|---|
| `X11/Xft/Xft.h` | libxft/2.3.9 |
| `X11/extensions/Xrender.h` | libxrender/0.9.12（**`Xft.h` 第 42 行直接 include 它**） |
| `fontconfig/fontconfig.h` | fontconfig/2.18.3（`Xft.h` 第 41 行 include） |
| `ft2build.h` | freetype/2.14.3，**位置是 `include/freetype2/ft2build.h`**（`Xft.h` 第 39-40 行 `#include <ft2build.h>` + `#include FT_FREETYPE_H`） |
| `X11/X.h` `X11/Xatom.h` `X11/keysym.h` | xorgproto/2025.1 |
| `X11/Xlib.h` `X11/Xutil.h` `X11/XKBlib.h` | libx11/1.8.13 |

⇒ **`_incdirs()` 里那条 `include/freetype2` 子目录不是防御性冗余，而是硬需求**：
`ft2build.h` 不在 `<freetype>/include/` 根上，只给 `-Iinclude` 编不过。
这正是上游 `config.mk` 写 `-I/usr/include/freetype2` 的原因，也验证了六个 require
一个都不能少。

libX11 的两条血脉里，`libx11/6.4.0` 需要 `libxcb/1.16`，`libx11/1.8.13` 需要
`libxcb/1.17.0`——注意 `archives/l/libxcb/` 下只有 `1.16` 与 `1.17.0.1` 两个目录，
**没有 `1.17.0`** 的本地归档目录。曾疑心这一节点是否真的存在；
实测 `libxcb/1.17.0` 在 ohpcd 制品仓**已发布且 OHOS 二进制可下载**（见 §7），风险解除。

`-lXrender` / `-lfreetype` 等**不写进 LIBS**：六个包 `default_options` 都是
`shared: True`（逐个 grep 过 conanfile），且下载下来的二进制包里
`lib/` 确实是 `libXft.so.2 / libfontconfig.so.1 / libX11.so.6 / libXrender.so.1 /
libfreetype.so.6 / libxml2.so.16` 一整套 `.so`，sent 不调用它们的符号，
运行期靠 `libXft.so.2` 自己的 `DT_NEEDED` 带进来。**已实测**（llvm-readelf -d）：

```
libXft.so.2        NEEDED libfontconfig.so.1 libfreetype.so.6 libXrender.so.1 libX11.so.6 libc.so
libfontconfig.so.1 NEEDED libfreetype.so.6 libxml2.so.16 libc.so
libX11.so.6        NEEDED libxcb.so.1 libXau.so.6 libXdmcp.so.6 libc.so
libXrender.so.1    NEEDED libX11.so.6 libxcb.so.1 libXdmcp.so.6 libXau.so.6 libc.so
```

⇒ 运行期**没有** `libfontenc`，fontconfig 走的是 **libxml2** 后端（注意
`fontconfig/2.18.3` 依赖 `libxml2/2.15.3`，而 `fontconfig/2.18.1.1` 依赖
`expat/2.8.2.1`，两条血脉不同）。test_package 的 `LD_PRELOAD` 顺序表就是照这
几行 DT_NEEDED 写的，不是凑的。

## 4. 裸 Makefile 的接线口径（配方核心决策）

`config.mk` 的关键五行：

```make
X11INC = /usr/X11R6/include
X11LIB = /usr/X11R6/lib
INCS = -I. -I/usr/include -I/usr/include/freetype2 -I${X11INC}
LIBS = -L/usr/lib -lc -lm -L${X11LIB} -lXft -lfontconfig -lX11
CFLAGS += -g -std=c99 -pedantic -Wall ${INCS} ${CPPFLAGS}
LDFLAGS += -g ${LIBS}
CPPFLAGS = -DVERSION="${VERSION}" -D_XOPEN_SOURCE=600
```

**注入点选 `INCS` 与 `LIBS`，不选 `CFLAGS`/`LDFLAGS`/`CPPFLAGS`。** 理由：

- `INCS`/`LIBS` 是普通 `=` 赋值 ⇒ make 命令行变量优先级最高 ⇒ 一次覆盖就把
  `/usr/X11R6`、`/usr/include`、`/usr/lib` 这些宿主路径**整体换掉**（这些路径在
  OHOS 上要么不存在、要么可能撞进别的 X 栈，属于 R26 污染面）。
- `CFLAGS`/`LDFLAGS` 是 `+=`。一旦把它们放到命令行上，GNU make 的规则是"命令行变量
  不被 makefile 里的赋值覆盖（除非 `override`）"，于是 `+=` 那行**整条失效**，
  `-std=c99 -pedantic -Wall` 和 `${CPPFLAGS}` 全部丢失。
- 尤其致命的是 `CPPFLAGS` 里带着 `-DVERSION="1"`。它一旦被丢，`sent -v` 会安静地打印
  `sent-`（VERSION 展开为空），二进制照样编得出来、照样"能跑"。
  ⇒ **test_sent.sh 的第 1 条断言就是专门钉这个的**：严格匹配 `^sent-1$`。
- 对比 `farbfeld/4.0`：它确实是在命令行上传 `CFLAGS=`/`LDFLAGS=`/`CPPFLAGS=`，并且为此
  在配方里把 `-std=c99 -pedantic -Wall -fPIC` 手工重建了一遍（`_cflags()`）。那是可行
  的，但重建清单容易和上游漂移。sent 这条 `INCS/LIBS` 路线不动上游 flags，改动面更小。

`-I.` 必须保留（`config.h` 是 make 现场从 `config.def.h` 拷出来的，`arg.h/util.h/drw.h`
也在源码根）。`-lm` 放在最后（链接规则是 `${CC} -o $@ ${OBJ} ${LDFLAGS}`，
`LIBS` 展开在对象之后，`-lm` 位置正确）。

`CC` 从 conan conf 取（R33），不裸用 shell `${CC}`：
`self.conf.get("tools.build:compiler_executables", ...)` 拿不到再 `shutil.which("clang")`。
`build()`/`package()` 都带 `env="conanbuild"`，让 AutotoolsToolchain 的 flags 通过 `+=`
追加进去。

## 5. install 接线与 `CC`/`STRIP` 不烤进产物

上游 `install` 目标：

```make
install: all
	@mkdir -p ${DESTDIR}${PREFIX}/bin
	@cp -f sent ${DESTDIR}${PREFIX}/bin
	@chmod 755 ${DESTDIR}${PREFIX}/bin/sent
	@mkdir -p ${DESTDIR}${MANPREFIX}/man1
	@cp sent.1 ${DESTDIR}${MANPREFIX}/man1/sent.1
	@chmod 644 ${DESTDIR}${MANPREFIX}/man1/sent.1
```

两个坑：

1. `${DESTDIR}${PREFIX}` / `${DESTDIR}${MANPREFIX}` 是**直接拼接、中间没有分隔符**。
   所以正确写法是 `PREFIX=`（留空）配 `MANPREFIX=/share/man`（自带前导斜杠）：
   `<pkg>` + `` + `/bin` = `<pkg>/bin` ✓；`<pkg>` + `/share/man` + `/man1` = `<pkg>/share/man/man1` ✓。
   写 `MANPREFIX=share/man` 会得到 `<pkg>share/man/man1`（少一个斜杠，被拼到上一级去）。
   （`abduco/0.6` 配方里就是 `MANPREFIX=share/man` 这个形态，不打算照抄。）
2. `install: all` 会先回头构建 ⇒ `package()` 里必须传**与 `build()` 完全相同**的
   `CC=/INCS=/LIBS=` 覆盖，否则那一次重编会用不同的 flag 集产物替换掉本轮编出来的东西。

**`CC`/`STRIP` 不会被烤进产物**：`grep` 过 `sent` 的 `Makefile` 与 `config.mk`，
上游**根本没有 `STRIP` 变量**（这点和 abduco 不同：abduco 有 `STRIP` 且默认会 strip，
OHOS 内核对 strip 过的 ELF 会拒），install 就是 `cp -f`，也没有 libtool 的 `.la` /
`-rpath` 脚本被安装。⇒ 本配方**不做任何 strip**，也不需要像 abduco 那样传 `STRIP=true`。
唯一要补的是 **OHOS ELF 自签**（`binary-sign-tool` + 先 `llvm-objcopy --remove-section .codesign`），
未签名内核直接拒执行——这一步在 `package()` 里对 `<pkg>/bin/sent` 做。
注意 HMDFS 上 `chmod` 可能被忽略（HMBS_CAP_CHMOD=0），签完的 `chmod` 用 try/except 容错。

## 6. 测试账本设计（**本轮不执行**）

### 6.1 上游测试清点（R51 第一步，静态）

`Makefile` 目标全集：`all` `options` `config.h` `.c.o` `sent` `cscope` `clean`
`dist` `install` `uninstall` `.PHONY`。⇒ **无 `check`、无 `TESTS`、无 `check-local`**。
包里也没有 `tests/`、没有 `test_*` / `*_test.c`。
`example/` 是示例演示文稿、`transparent_test.ff` 与 `nyan.png` 是 example 引用的素材
（文件名里的 "test" 是素材名，不是测试）。

**上游静态测试总数 = 0。** 证据已写进 `test_package/MANIFEST.yml` 的
`upstream_test_audit`。

### 6.2 五维打算

| 维度 | 打算值 | 说明 |
|---|---|---|
| 静态总数（上游） | **0** | 上面清点结论；`make check` 无规则 |
| 可执行数（上游） | 0 | 无可执行的上游用例 |
| test_package 静态断言数 | **6** | 4 条真实执行 + 2 条存在性，脚本内 `[exec]`/`[file]` 前缀显式区分 |
| 实测通过 / 跳过 / 失败 | **6 / 0 / 0** | 2026-09-28 W3 真实执行轮（收尾-2B），实测行见 §9：`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":6,"passedCount":6}` |

`discovered=6` 是 `test_sent.sh` 自己数出来的，`HMBS_TEST_PACKAGE_RESULT` 打印的
`passedCount` 与之一致，不手填。

### 6.3 sent 可无显示执行的路径（读 `sent.c main()` 得到；2026-09-28 已真机实测 6/6，见 §9）

`main()` 的顺序决定了哪些路径碰不到 X：

```c
ARGBEGIN {
case 'v':  fprintf(stderr, "sent-"VERSION"\n"); return 0;   /* ← 无 X */
default:   usage();                                          /* ← die()→exit(1)，无 X */
} ARGEND
if (!argv[0] || !strcmp(argv[0], "-")) fp = stdin;
else if (!(fp = fopen(fname = argv[0], "r")))
    die("sent: Unable to open '%s' for reading:", fname);     /* ← 无 X */
load(fp);
if (!slidecount) usage();                                     /* ← 无 X */
xinit();                                                      /* ← XOpenDisplay(NULL) */
run();
```

`util.c:die()` 恒定 `exit(1)`，且 fmt 以 `:` 结尾时走 `perror(NULL)`。
`xinit()` 里 `XOpenDisplay(NULL)` 失败 ⇒ `die("sent: Unable to open display")` ⇒ exit 1。

⇒ 四条**确定在 xinit 之前返回**、因而不需要 `$DISPLAY` 的路径，全部用作断言：

1. `sent -v` → rc **0**，输出严格 `sent-1`（写到 **stderr**；`sent.1` 手册页却写
   "to stdout"，上游文档与实现不一致 ⇒ 脚本按 `2>&1` 合并捕获，不断言 fd 归属）。
2. `sent -Z`（未知选项）→ rc **1**，输出含 `usage: <argv0> [file]`；
   `arg.h` 的 `ARGBEGIN` 里 `argv0 = *argv`，所以断言里 grep 的是**被测二进制的绝对路径**
   本身 —— 只有真正被执行的那个二进制才会打印出这个 argv[0]，桩/错位产物过不了。
3. `sent /nonexistent/...txt` → rc **1**，输出含 `Unable to open`。
4. `sent - < /dev/null` → rc **1**，输出含 `usage:`（空输入 ⇒ `slidecount==0` ⇒ `usage()`）。

**故意不测的路径**：喂一份真能解析的演示文稿。因为那会走到 `xinit()`；
若 CI 宿主恰好导出了可用的 `DISPLAY`，`sent` 会真的开窗口并进入 `run()` 事件循环
**永久阻塞**，把 CI 挂到超时。headless 下它虽然会以 `Unable to open display` 退出、
顺带证明 X11 动态链接成功，但收益不值这个风险——**动态链接其实已经被断言 1 证明了**：
共享库的 `DT_NEEDED` 在 `main()` 之前由加载器解析，缺库根本进不到 `main`
（会是 rc 127 / `CANNOT LINK EXECUTABLE`）。脚本仍打印 `ldd` 输出作为诊断（不判言）。

**"真实执行" 与 "只检查文件存在" 的区分**：断言 1–4 是真实执行被测二进制；
断言 5（`share/man/man1/sent.1`）与 6（`licenses/LICENSE`）只是存在性检查，
脚本里用 `[file]` 前缀标出，不算进"执行了二进制"的数目。

## 7. W0 结论（已实测）

`bash ci/scripts/preflight_check.sh sent/1` → **退出码 0**，6 个精确依赖全部
`[OK] 已发布`，且 `版本号未被占用: sent/1`。
传递闭包另用 `--deps` 探了 16 条（含 `libxcb/1.17.0`、`libxdmcp/1.1.5`、
`libxml2/2.15.3`、`xtrans/1.4.0`、`xcb-proto/1.17.0`），同样全部已发布。

再叠一层**二进制**级证据（preflight 的 `conan download --only-recipe` 只证明
**配方**在仓，不证明有 OHOS 二进制，R35 的老坑）：

```
conan install --requires=libxft/2.3.9 --requires=fontconfig/2.18.3 \
  --requires=libx11/1.8.13 --requires=libxrender/0.9.12 \
  --requires=freetype/2.14.3 --requires=xorgproto/2025.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=never
→ Download (ohpcd) 10 个包，Install finished successfully，退出码 0
```

用的是**仓内真实 OHOS profile**（`os=OHOS / os.version=6.0 / arch=armv8 /
clang 15 / Release`），不是手搓 profile，所以不存在 "Missing prebuilt package"
假阴性。这一条同时**实测**排掉了 §3 里"混用 libxft 与 libx11 会不会撞版本"的顾虑：
一条命令里同时装这六个包能解析出单一闭包 ⇒ **无版本冲突**。
`-pr:b=default` 会报 `Profile not found: default`（隔离 CONAN_HOME 里没建过默认
profile），要把 `ohos-aarch64` 同时当 host 和 build。

### ⚠ 一个差点误报成"依赖全未发布"的坑（值得跨库复用）

第一次跑 preflight 时 **6 个依赖全部报 `[WARN] 未发布`、退出码 1**，差点按
R36 / AGENTS §8 W0 的口径停下汇报"依赖未发布、需先转手上游"（`$P block`）。

真因：本轮用的是**新建的隔离 `CONAN_HOME`**（`~/tmp/ch/home-主理-6-sent`），
里面**根本没有 `ohpcd` remote**（`conan remote list` 只有 `conancenter`）。
preflight 的探测是 `conan download "$dep" -r=ohpcd --only-recipe` 且只看退出码
（`>/dev/null 2>&1`），remote 不存在 ⇒ **任何 ref 都失败** ⇒ 全量误报未发布。

`ohpcd` remote 是 **CI 机预部署**的，由 `ci/conan/setup.sh` 补：
```
CONAN_REMOTE_URL="https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/"
conan remote add --force ohpcd "$CONAN_REMOTE_URL"
```
而 **preflight 自己不做这一步**。⇒ **在隔离 CONAN_HOME 里跑 preflight 之前，必须先手动加 remote。**

**防误报的固定动作**：跑 preflight 前先加**正对照**（拿已知已发布的 ref 试
`conan download -r=ohpcd --only-recipe`），再加**负对照**（故意编造的 ref 应当
NOTFOUND）。本轮实测：未加 remote 时 `zlib/1.3.1` 也 NOTFOUND ⇒ 判"探测无效"；
加好后 `zlib/1.3.1` / `libx11/6.4.0` / `libxcb/1.16` PUBLISHED，而
`xorgproto/2024.1` 与 bogus ref NOTFOUND ⇒ 判"探测有效且有区分度"，此时
preflight 的结论才可采信。
**没有对照组就把 preflight 报成"依赖未发布"，等于拿一次配置缺失去做 block/转手决策。**

## 8. 遗留 / 风险（下一轮要确证的）

1. 全部**构建期**结论仍未实测：扁平归档的 `get()` 落点、`INCS/LIBS` 覆盖后能否真编
   出来、`make install` 的 `chmod` 在 HMDFS 上是否报错、ELF 自签是否成功。
   本轮按主理限定没有起构建。
2. `package()` 里 `make install` 会因 `install: all` 重跑构建：若 conan 在 package
   阶段拿到的 `self.dependencies[*].package_folder` 与 build 阶段不一致（缓存路径
   变化），`INCS/LIBS` 字符串会变、触发重编。届时改成把 flag 集在 build 期固化进
   临时文件复用。
3. 运行期字体回退：`config.def.h` 里 `fontfallbacks[] = {"dejavu sans","roboto","ubuntu"}`
   ⇒ 真机要**显示内容**需 fontconfig 能匹配到这些族（本闭包的 DT_NEEDED 里没有
   `libfontenc`，字体目录映射全靠 fontconfig 自带配置）。这不影响 rc 层面的断言，
   但影响"能不能真用"，R40 意义上的深度适配需真机确认（本轮不做）。
4. test_package 的 `LD_PRELOAD` 由 `_runtime_preload()` 生成，而 conan 的
   `self.dependencies` 只暴露直接依赖 ⇒ 那 9 个 X11 库大概率取不到、preload 会退化成
   空串（xeyes 同款行为），实际寻库主通道是 `VirtualRunEnv` 注入的
   `LD_LIBRARY_PATH`。脚本会把两者都打印出来，真机一眼能看出走的哪条。
   若真机报缺库，修法是在 test_package 里把这几个包也 `requires` 成直接依赖。
## 9. 最终状态（2026-09-28 构建执行轮，收尾-2B/qw2-sent）

**W3 = conan-verify 判绿（三一致）**：判决文字全 PASS（G0-G4、L2/L4/L5）+ `**Verdict**: PASS` + 退出码 0。
证据：`reports/conan-verify-report.md`、`reports/conan-create.log`（含 `Calling build()`）、
`reports/w3-local-ci.log`（`build_and_test.sh` 本地 CI 等效检查通过）、`.ci-result.json`
（exit_code=0，finish 工具写入，带 integrity_hash 与日志 SHA256）。

### 本轮构建期实测出的三颗雷（已修）

1. **Conan 1.x 导入**：配方原写 `from conan.tools.env import AutotoolsToolchain`，conan 2.29.1 里
   `AutotoolsToolchain` 在 `conan.tools.gnu`，`conan create` 导出即 ImportError。已拆分导入。
2. **单字符版本非法**：`conan/api/model/refs.py` 校验 `^[a-zA-Z0-9_][a-zA-Z0-9_+.-]{1,100}$`
   要求版本 ≥2 字符，`sent/1` 导出即 `Invalid package version '1'`。按 cronic/v3、rapidhash/v3、
   cutmp3/4.0、dbskkd-cdb/3.00 同型先例：目录与分支保留任务卡值 `1`，配方 `set_version()`
   归一制品版本为上游发布标识 `v1`（发行物 `sent-1.tar.gz` 即 "sent, v1"）。
   **制品仓真实引用 = `sent/v1@ohpcd/stable`**；commands.json 的版本键按 PF8 机械口径保持 `1`/`sent/1`。
3. **运行期加载（跨包可复用）**：
   - 制品仓发布的 **fontconfig/2.18.3、libxft/2.3.9** 二进制**签名失效**：`.codesign` 节在，但加载器
     从任何路径拒载（LD_LIBRARY_PATH、LD_PRELOAD、精确 DT_NEEDED 名副本全报
     `Error loading shared library`），同批其余 7 库正常（E135 族：签名无效与缺失同罪）。
   - 对策：test_package 把 9 库闭包按 **SONAME 名**拷入 `$TMPDIR` scratch 目录，逐个
     `binary-sign-tool -selfSign 1` 重签（llvm-objcopy 先剥旧 `.codesign`），目录作 argv[3] 传给
     `test_sent.sh` 置顶 LD_LIBRARY_PATH；重签失败自动退回原始路径（脚本 $3 为可选参数，向后兼容）。
   - `_find_so` 排序改为「非链接优先 → 尺寸下限 → 最长文件名」：HMDFS 懒物化 `libXft.so.2`
     符号链接（mtime=首测时刻），首测把未物化链接名交给加载器导致 Xft 全系 reloc 失败（E050）。
   - 手工实证：重签副本 + 置顶搜索路径后 `sent -v` 打印 `sent-1`、正常退出（rc=0）。

### 测试账本实测（rule4：声明数 ≤ 实测数）

- 上游静态测试总数 = **0**（`test_package/MANIFEST.yml` audit，R51；Makefile 无 check/TESTS、无 tests/）。
- test_package 断言：设计 6 = 实测 6；**实测通过 6 / 跳过 0 / 失败 0**
  （4 条 `[exec]` 真实执行被测二进制 + 2 条 `[file]` 存在性），
  实测行：`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_sent.sh","discovered":6,"passedCount":6}`。

### K0 实拍（打包后二进制，LD_LIBRARY_PATH 置顶重签副本目录）

- `sent -v` → 输出 `sent-1`，**rc=0**。
- `sent --version` → `usage: <bin> [file]`，**rc=1**；`sent --help` → 同，**rc=1**。
  上游 suckless `arg.h` 没有长选项，`usage()` 即上游唯一的"帮助/版本错误"路径（test_package
  断言 2 正是钉这一行为并校验 argv[0] 绝对路径）；长选项 rc≠0 是上游事实，如实记录，非适配缺失。

### 框架噪声记录（不改框架，只绕行）

- `ohc-run.py build sent 1` 的 Step1 走 `archives/s/sent-1/src` 旧码路并猜测 URL（sent.io 等），
  对已有手写配方不可用 → 直接 `conan-verify`（G2 = 自包含 conan create，用 conandata 官方源）。
- finish 的 [3/10] clean-verify 因无本地 src tarball 跳过（平台限制，非阻塞）→ finalize-archive
  缺 release/debug tar.gz 报 RC=2 警告；Step8 gen_summary 'str has no append'（框架已知缺陷）。
  框架终判 `EXIT_REASON: finish_success`，`.ci-result.json` 已由工具写入。
- 引擎在失败轮误命中 E416/E225/E520（均与真实根因无关），真实根因以上文三条为准。

## 10. 路径 B 声明（3+2 行）

- 适配路径：路径B（知识库扩展）
- 使用知识库：是——knowledge/drafts/DRAFT-10491-sent-1-libxft-hardpins-libx11-18-blocks-64-lineage（成对 .kv/.md 随本分支提交，draft-review 最高相似 E538=0.10，判 create）
- 知识库扩展：libXft 硬 pin libx11/1.8.Z，与已审 libx11/6.4.0 血脉互斥；凡经 libXft 取字体的 X 客户端不得照抄 xeyes 的 6.4.0 口径，正解是只 requires libxft 让整条栈传递解析
- 关联 Issue：#3545（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3545，2026-09-28 由收尾-5 创建）
---

**编译结束**: 2026-09-28 12:39
**最终状态**: built
