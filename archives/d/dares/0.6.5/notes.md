# dares 0.6.5 — HarmonyOS PC 移植说明

## 软件身份

- dares = **DAta REScue**（c't Magazin，2002/2005，Oliver Diedrich）：从受损
  CD/DVD（ISO9660 镜像或设备）中按内容抢救文件的工具，C + ncurses TUI。
- 版本内证：`include/global.h` → `#define VERSION "dares 0.6.5"`。
- License：GPL-2.0-or-later（源码头注释 GNU Public License；tarball 内无独立
  COPYING 文件，故 package() 未拷贝 license 文件）。
- 源码归档：`dares_0.6.5+repack.orig.tar.gz`（Debian pool，与 Debian .dsc 核对）。
  SHA256 = `6be06bd9c331166a50b516d0cca09a7c97cbfedac78f3e779cfe4d2e92e342e2`
  （64 位实测值；设备上下载后 hashlib 实算核对）。

## 构建系统与移植策略

- 手写递归 Makefile，**无 configure / 无 CMake / 无 install target**。
- 顶层 `all: qt ncurses`：qt3 前端上游已废弃（qt 依赖 qmake），OHOS 无 qt3，
  **必须跳过**。recipe 不调顶层 Makefile，直接在 `frontend/ncurses/` 内 make，
  仅构建 ncurses 前端。
- `frontend/ncurses/Makefile` 硬编码 `CC=gcc`、`CFLAGS=-g -O2 -Wall`、
  `LDFLAGS=-Wall -lncurses -lmagic`，且链接规则为
  `$(CC) $(LDFLAGS) -o dares $(OBJ)` —— 库在目标文件**之前**。
  0001 补丁（最小、可解释）：
  1. `CC/CFLAGS/LDFLAGS` 改为 `?=`，新增 `CPPFLAGS ?=` —— 变量可被 make
     命令行/环境覆盖（Linux 下裸 `make` 行为不变，默认值原样保留）。
  2. 链接规则改为 `$(CC) -o dares $(OBJ) $(LDFLAGS)` —— 依赖 ncurses 6.6 与
     file 5.48.1 都是**静态库**（R26），静态归档必须在目标文件之后出现，
     否则符号无法解析。
- OHOS 链接：`-lncursesw`（宽字符，E033/E028）+ `-lmagic`，include/lib 路径由
  recipe 从 `dependencies["ncurses"|"file"].package_folder` 注入（E277/E524
  依赖注入/前缀隔离模式）。

## 依赖消费方式（与 abook 的差异）

- abook 0.6.1 走 cmd-pkgs 系统安装 ncurses/readline；dares **不走 cmd-pkgs**：
  - libmagic 不是 cmd-pkgs 供应集的一员，仓内由 `file/5.48.1` recipe 以 conan
    包提供（静态 `libmagic`，`cpp_info.libs=["magic"]`）；
  - dares 是**仓内首个 `-lmagic` 消费者**（file 5.48.1 的 pkg_config_name
    `libmagic` 曾为 rizin 记录，但 dares 是首个直接 `-lmagic` 链接者）。
- 因此采用 `self.requires("ncurses/6.6")` + `self.requires("file/5.48.1")`
  （ohpcd 制品仓两者均已发布，L0i R36 核验通过）。

## magic 数据库打包决策（记录理由）

dares 的加载顺序（`backend/dares.c`）：

1. `magic_load(cookie, MAGIC_FILE)`，`MAGIC_FILE "magic"` —— **相对 CWD**
   （`-m` 时对应 `magic.mime`）；
2. 失败则打印 "Could not load ..."，回退 `magic_load(cookie, NULL)` ——
   libmagic 编译期默认路径，失败时再取 `MAGIC` 环境变量。

**实证（设备对照实验矩阵，2026-09-11）：**

- 上游自带的 `magic`（file-3.x 时代语法，11058 行）在 libmagic 5.48.1 下
  **解析失败**：告警超限后 load 返回 -1 → 分类失效（found 0 files）。
- 预编译 libmagic 的编译期默认路径已损坏：无任何 magic 时尝试打开
  `//share/misc/magic` → found 0 files。
- **显式路径加载编译版 magic.mgc 必然失败**：CWD 放置 mgc 后
  `magic_load(cookie, "magic")` 仍返回 -1（apprentice_map 拒绝后按源码
  格式重解析二进制内容亦失败）→ found 0 files。
- **`MAGIC` 环境变量回退路径是唯一可用路径**：`MAGIC=<file/5.48.1 包内
  magic.mgc>` 时 → `found 1 files`、真实分类 "ASCII text"、文件抢救落盘。

**决策：随包安装 libmagic 5.48.1 的编译版 magic.mgc + 注入 MAGIC 环境变量。**

（机理已知识化：`knowledge/drafts/DRAFT-magic-db-load-path-fallback.kv/.md`——
libmagic 运行时四路加载路径矩阵与消费者数据闭合部署模式，自包含复现探针见该草稿。）

- package() 从 `file/5.48.1` 依赖包复制 `share/misc/magic.mgc` →
  `<pkg>/share/dares/magic.mgc`（与链接的 libmagic 严格同版本）；
- `package_info` 注入 `runenv MAGIC=<pkg>/share/dares/magic.mgc`，回退路径
  在任意 CWD 都命中真实数据库（上表 case 2 实证可用）；
- "Could not load file magic database file 'magic'" 是 CWD 首路径未命中时
  的固定提示，属预期噪音，test_package 不对其断言，而以真实分类结果
  （found/Saving/抢救文件落盘）作为功能断言；
- **不打包**上游自带 `magic`/`magic.mime`（时代错配，加载即失败，装了反而
  有害），理由与证据如上；
- 不采用「编译期把 MAGIC_FILE 指到绝对包路径」：会把设备/包绝对路径写进
  源码补丁，违反移植规范（且无必要）。

## 上游测试套件：无（NO_UPSTREAM_TESTS）

实证核对（tarball `dares_0.6.5+repack.orig.tar.gz`，SHA256 见上）：

- 完整文件清单 17 个文件（含 7 个废弃 qt3 前端文件：`frontend/qt/{Makefile, qt.pro,
  main.cpp, daresview.{h,cpp}, paramsdialog.{h,cpp}}`）：`backend/dares.c`、
  `frontend/ncurses/{Makefile,display.c}`、`include/{dares.h,global.h}`、
  `doc/{HISTORY,README.deutsch}`、`Makefile`、`magic`、`magic.mime`；
- 无 test/ 目录、无 `*.test`/`check` 文件、无 configure/CMakeLists.txt；
- 两个 Makefile 的 target 仅 `all/qt/ncurses/clean`（顶层）与
  `dares/clean/all`（ncurses 前端），**无 check/test target**。

结论：`NO_UPSTREAM_TESTS`，discovery.status = EVIDENCE_COMPLETE。功能验证由
test_package 自建冒烟承担（见下）。

## test_package 设计（自建冒烟，非交互）

dares 的退出码语义特殊：除 autosave 路径外**一律 exit 0**
（`daresClose()` 恒返 0，包括无效参数路径），因此断言全部基于 stdout 内容；
autosave 路径保存完成后 `exit(1)`（by design），用 `ignore_error=True`。

关键发现：扫描发现文件后默认进入 ncurses 文件列表 UI（initscr），CI 中不可
交互；`-a`（autosave）在 UI 之前抢救并退出 —— 这是唯一覆盖「真实扫描 +
libmagic 分类 + 文件落盘」的非交互路径。

1. 无参数运行 → usage banner 含 `DAta REScue dares 0.6.5`；
2. `dares --version` → 确定性错误诊断 `argument '--version' invalid` + usage；
3. 空镜像扫描 → `finished: scanned 0 2K blocks, found 0 files`，exit 0；
4. 真实抢救：640×17B 文本 = 10880B（5 个 2048B 块）镜像 + `-a` →
   `contains 5 blocks`、无 `Could not load`（CWD magic 库真实加载）、
   `found 1 files`、`Saving 1 files`、抢救文件 `*.asc` 落盘；
5. `-m -a` 变体 → magic.mime 加载成功（无 `Could not load ... 'magic.mime'`）。

## 风险与备注

- dares 2005 年代 C 代码（`sprintf`/`strncpy` 等）在 clang 15 下仅告警；
  `O_BINARY` 已由 `dares.h` 处理（非 DOS 平台定义为 0），源码可移植性好。
- package_type=application + bindirs=bin，L0k R38 要求的
  `archives/d/dares/commands.json` 已建。
- 上游主页 http://www.heise.de/ct/projekte/dares（c't 项目页，活动性弱）；
  源码以 Debian pool 归档为准。
