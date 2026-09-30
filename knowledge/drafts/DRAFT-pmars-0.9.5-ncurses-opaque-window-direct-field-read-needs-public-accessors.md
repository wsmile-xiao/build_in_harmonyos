# 制品仓 ncurses/6.x 是不透明 WINDOW 发布：直读 `curwin->_curx/_cury` 是硬编译错误，必须换公共访问器 `getcurx()/getcury()`（也别自造字段别名宏）

> 触发实测：**pmars 0.9.5 / 任务 9605**，2026-09-26，B 机（HarmonyOS PC aarch64，8 核 / 31G），
> conan 2.29.1 + `ci/conan/profiles/ohos-aarch64` + clang 15（`aarch64-unknown-linux-ohos`）。
> 取用方式：复制为 `DRAFT-<你的包>-<你的版本>-ncurses-opaque-window-direct-field-read-needs-public-accessors.{kv,md}`，
> 把下面所有读数换成本包实测值。**只有本包真报出那个签名才配这条。**

## 一句话

本仓制品 `ncurses/6.6` 的 `include/curses.h:152` 就是 `#define NCURSES_OPAQUE 1`，`WINDOW` 只剩一句
`typedef struct _win_st WINDOW;`（没有成员声明）。于是上游那些"按 K&R 习惯直读窗口内部字段"
的代码，在**配方构建阶段**就是 `incomplete definition of type 'struct _win_st'` —— 硬错误，
不是警告，补 `-I`、关 `-W`、换优化级别都救不了。正确解法只有一条：改用 ncurses 的**公共访问器**
`getcurx()` / `getcury()`。

## 症状（pmars 实测逐字）

`src/curdisp.c` 里有 5 处成员直读，首编逐处报出同一签名（行号 464 / 465 / 466 / 468 / 480）：

```
src/curdisp.c:464:20: error: incomplete definition of type 'struct _win_st'
  if (ox = curwin->_curx) {
           ~~~~~~^
src/curdisp.c:44:13: note: forward declaration of 'struct _win_st'
```

制品侧的成因一眼可核（三条读数都出自本次构建实际用的那份包）：

```
include/curses.h:152   #define NCURSES_OPAQUE 1
include/curses.h:456   typedef struct _win_st WINDOW;        ← 只有 typedef，没有成员
nm --defined-only lib/libncursesw.a | grep -E ' T getcur(x|y)$'
                       0000000000... T getcurx
                       0000000000... T getcury               ← 访问器是真导出函数，不靠头文件内联
```

## 两个会误导人的地方

1. **签名长得像"头文件没装好"**。第一反应是去查 `includedirs`、补 `-I`、或怀疑 ncurses 依赖没发布。
   但 `typedef` 在、成员不在，说明**制品是故意不透明发布的**，路径怎么补都拿不到成员声明。
2. **"我本机编得过"**。带老式兼容声明的主机上同一份上游源码能编过，于是这条机制在开发侧
   隐形、只在配方侧显形。凡是"本地绿 / 配方红"且错误落在 curses 字段读取上的，先按本条查。

## 正确修法（pmars 的补丁形状）

单文件、两个 hunk、**行数不变**、不引平台宏、不加编译开关：

```c
- if (ox = curwin->_curx) {
-   mvwaddch(curwin, curwin->_cury, --ox, ' ');
-   wmove(curwin, curwin->_cury, ox);
+ if (ox = getcurx(curwin)) {
+   mvwaddch(curwin, getcury(curwin), --ox, ' ');
+   wmove(curwin, getcury(curwin), ox);

- oy = curwin->_cury - 1;
+ oy = getcury(curwin) - 1;
```

算术留在访问器**外面**（别把 `getcury(w)-1` 塞成宏位上的表达式），读语义与上游完全一致。
补丁后：该签名 0 命中、`BUILD_RC=0`、`conan create` 的 G1/G2/G3 全 PASS，
13 条消费者断言 13/13 通过（其中 6 条是上游作者写在 `.red` 语料里的 `;assert`，由 pmars
自己的装配器在 `-A` 阶段真求值）。

## 两条看起来能省事、实际不能走的路

- **自造字段别名宏**：仓内就有这个方向的先例（`nwipe/0.39` 在 conanfile 里塞
  `int _cury, _curx;` + `#define getcurx(w) ((w)->_curx)`）。那等于**自己声明一套与制品布局
  不一致的结构**：链接能过，但读出来的坐标是错的 —— 把编译期硬错误换成运行期静默错值，
  比原问题更贵。公共访问器本来就是 ncurses 为这个场景提供的，没有理由绕过它。
- **用 `-DNCURSES_OPAQUE=0` 把不透明性"解开"**：这是在跟制品的发布形态对赌，
  且会连带改变该编译单元里**所有** curses 声明的可见性（包括别的包版本带来的头），
  属于把一处问题扩散成一片不确定性。

## 顺手一条：链接名

本仓 curses 制品的链接名是 **`-lncursesw`**（wide 版）。写成 `-lcurses` 会在链接期以**另一副
面孔**失败（`undefined symbol` 一类），**别把两次失败混写成同一条机制** —— 那是两个签名、两个解法。

## 边界（这条不是什么）

它是**纯编译期类型可见性**问题：不碰 syscall、不碰 ioctl、不碰设备节点，而且**不是 OHOS
特有的**——触发面锚在本仓制品 `ncurses/6.6`（`include/curses.h:152` 即
`#define NCURSES_OPAQUE 1`）上，同一份上游源码在任何 `NCURSES_OPAQUE=1` 的 ncurses ≥6
（含普通 Linux 发行版）里都会报出同一签名 ⇒ 它是**上游与 ncurses 6 的通用兼容修复**。
⇒ 在 PR 正文或 notes 里把它叙述成"OHOS 平台能力缺失""鸿蒙特有""终端被限制"是**不实陈述**；
把它当成"OHOS 新知识"来申报 B 属**过度归因**（2026-09-26 W4 r1 独立审计的结论，本窗接受并
据此收紧措辞）。本包真正的 OHOS 特有面是另两条：**X11 只能编译期关闭**（`src/Makefile:22` 是
`CFLAGS +=`、`:26` 硬编 `-L/usr/X11R6/lib -lX11`，故必须改驱动 `Makefile.clang`）与进 curses
显示需要 `requires("ncurses/6.6", run=True)` 把 runenv 的 `TERMINFO`/`TERMINFO_DIRS` 带过去，
缺了就 `ncurses: cannot initialize terminal type` + `rc=1`（后者与已发布先例 presage 同族，
**不另报成新知识**）。

## 查重记录（2026-09-26，本窗一手）

| 查法 | 结果 |
|---|---|
| `knowledge/graph` 与 `经验文档/` 全域 grep `getcurx` / `NCURSES_OPAQUE` / `_curx` / `incomplete definition of type` | **零命中**（无任何登记条目描述本机制） |
| 本包 PR 提交前跑 harness `scripts/ohc-run.py draft-review <本 draft_id>` | 质量预检 `signature=✅ root_cause=✅ rec=✅`；相似 TOP3 = **E020 0.14 / E404 0.14 / E102 0.00**；预审建议 **create** |
| 仓内实现先例（**不是知识条目**，只证明"成因形状"出现过） | `libgnt/2.14.0`（`NCURSES_OPAQUE_PANEL 1` → `panel_window()`）、`plotutils/2.6`（libpng 不透明 → `png_jmpbuf()`）；反方向先例 `nwipe/0.39`（自造 `#define getcurx(w) ((w)->_curx)`） |

**与最接近的已登记条目 E020 的边界**（说清为什么不套它）：E020 的对象是 **musl libc 的 `FILE`**
（`_IO_read_ptr`/`_IO_write_ptr` 一类内部字段），成因在 libc 头文件；本条的对象是
**ncurses 的 `WINDOW`**，成因在**本仓 ncurses 制品把 `NCURSES_OPAQUE` 置 1**，
可用解法是 ncurses 自己的公共访问器 `getcurx()/getcury()`（由 `libncursesw.a` 以函数导出，
`nm` 可回读 `T getcurx` / `T getcury`）。签名不同、库不同、访问器不同 ⇒ 按
"引用要精确 + 既有条目没写的另一条解法即升 create" 的口径单独成条，不套 E020。

## 哪些包该先怀疑这条

链本仓 ncurses/6.x 的 curses/终端 UI 家族：pmars、abook、libgnt、nwipe、mpd、各类 TUI
监控器与游戏。自查一行：

```
grep -rnE '->[[:space:]]*_cur[xy]\b' src/ **/*.c
```

非空即命中本条的形状。另外，"不透明 struct → 公共访问器"这个**成因形状**在 libpng
（`png_jmpbuf()`）、panel（`panel_window()`）上仓内都各自出现过实现先例，但签名与解法都不同，
那两类**不在本条覆盖范围内**，撞上了要各自单独取证。
