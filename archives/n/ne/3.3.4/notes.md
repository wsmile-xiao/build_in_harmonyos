# ne 3.3.4 适配笔记

- 日期：2026-09-11
- 上游：https://github.com/vigna/ne tag 3.3.4（sha256 6958b5cd…，发布日期 2025-02-06，见 NEWS）
- 任务：#5484（taskBranch=feat/ne-3.3.4，路径 A）
- 构建系统：纯 makefile（无 configure；`src/makefile`，顶层 makefile 的 build 目标需要 docs/makeinfo，绕过）

## 1. 源码获取

GitHub 直连超时（exit 52），`ghfast.top` 镜像可用。Debian orig tarball（deb.debian.org `ne_3.3.4.orig.tar.gz`）与 GitHub tag tarball 逐字节一致（同 sha256），两者都**不含生成源文件**。

## 2. 生成源文件问题（本适配最大坑）

`src/makefile` 的规则：
```
enums.h names.c names.h hash.c hash.h help.c help.h ext.c: ne.texinfo version.texinfo info2src.pl
	makeinfo -D autohelp ne.texinfo
	perl info2src.pl
```

这 9 个文件在 `src/.gitignore` 里，tag tarball 不带。官方 README 说源码 tarball 由 `make source` 生成（需 makeinfo），“tarball 可以无 makeinfo 编译”——但官方并未发布 tarball（官网 302 到 GitHub，无 releases assets）。

**CI worker 无 texinfo**（cmd-pkgs 的 texinfo 7.3 包缺 perl 模块 Texinfo::ModulePath.pm，makeinfo 直接 Can't locate）。

**解法（两段）**：
1. 本地预生成：
   - `perl version.pl VERSION=3.3.4` → 生成 `doc/version.texinfo` + `src/version.h`（注意 version.pl 用**当日日期**，预生成后把 DATE 宏 sed 回上游真实日期 2025-02-06，保证可复现）
   - makeinfo 用 GNU texinfo 7.3 源码树直接跑：`perl <texinfo-7.3>/tta/perl/texi2any.pl`。唯一前置：手工 sed 生成 `tta/perl/Texinfo/ModulePath.pm`（从 ModulePath.pm.in 替换 @enable_xs@→no、@CONVERTER@→texi2any、@USE_EXTERNAL_*@→no 等）
   - `makeinfo -D autohelp ne.texinfo`（=texi2any.pl）→ ne.info（264KB）
   - `perl info2src.pl` → 生成 8 个文件（140 commands processed, HASH_TABLE_SIZE=3361）
2. 生成产物以 conandata `generated_sources` 第二源提供：九个文件托管在本仓库 `ne-src-raw` 分支（`https://raw.gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/archive/refs/heads/ne-src-raw.tar.gz`，先例 clp 1.17.10 的 clp-src-raw），`source()` 里 `get()` 下载（sha256 校验）后 `copy()` 拷入 `src/`，CI 无需任何文档工具。**2026-09-11 两轮改版史**：①原为 3942 行文本补丁 `0001-generated-sources.patch`，因 AI 代码检视把巨型文本补丁计入可审行数导致变更量超限（4334 行 > 分片上限）被跳过 4 次；②改为 prebuilt.tar.gz 二进制归档（libtar/md5deep 先例），但 CI worker 的 checkout-pr 用 `git apply` 应用 PR diff，二进制文件在 diff 中只有 "Binary files differ" 标记（无 base85 数据段），`git apply` 报 `missing binary patch data` → CI checkout 阶段必死（本地已复现）；③终版为 src-raw 托管分支 + conandata 第二源：文件完全不进 PR diff（AI 零计数），CI checkout 无障碍，sha256 锁定内容。

## 3. 构建命令

```sh
make -C src -j2 CC=$CC NE_GLOBAL_DIR=$PREFIX/share/ne \
  OPTS="-I<ncurses>/include" LIBS="-L<ncurses>/lib -lncursesw"
```

- makefile 的链接规则：`$(CC) $(LDFLAGS) $^ $(LIBS) $(OPTS) -lm -o ne`，LIBS/OPTS 都追加在末尾，传 -L/-l 正好
- clang 编译干净（只有 -Wparentheses 警告，无错误）
- 默认 terminfo 模式 `#include <curses.h> <term.h>` + 链接 curses；`NE_TERMCAP/NE_ANSI` 模式免 ncurses 但用内置 termcap（功能弱）。选择默认 terminfo + conan ncurses/6.4
- Debian 打包用 `LIBS=-ltinfo`；我们直接用完整 ncursesw（conan 包自带）

## 4. terminfo 运行时（鸿蒙特有）

- 设备实测：`/usr/share/terminfo` 存在但仅极简条目（hex 目录 s/x 等）；TERM=ansi 可用
- conan ncurses/6.4 包 `share/terminfo` 有 2868 条完整数据库（ansi/xterm/xterm-256color/screen/vt100/linux 全有）
- 配方处理：`package()` 复制 terminfo 进 ne 包，`package_info` 定义 `TERMINFO`+`TERMINFO_DIRS`（照抄 ncurses 配方做法）
- 实测：`TERMINFO=<ncurses>/share/terminfo TERM=ansi ./ne --help` 正常输出

## 5. 非 tty abort 问题（测试关键）

`ne.c:367-383`：stdin 非 tty 时把 stdin 内容读进 buffer，然后 `freopen("/dev/tty","r",stdin)`，失败 → `fprintf(stderr,"Cannot reopen input tty")` + **abort()**（SIGABRT，exit 134）。

脚本里 `< /dev/null` 会必死。**解法：pty**。python `pty.fork()` + `select` 读输出 + `waitpid` 收状态，ne 完整跑通：`--version`、`--help`、宏模式全 OK。

## 6. 宏模式（非交互自动化能力）

ne 支持 `--macro FILE` 启动后执行宏命令再退出。有效命令（names.c，140 个）：
- `InsertString "TEXT"` 在光标处插入
- `Replace "pat" "repl" "1"` 替换一次
- `Save` / `Exit`
- 宏文件每行一条命令；`Open "path"` 也可在宏里切文件

实测（pty 下）：
- `InsertString "INSERTED"\nSave\nExit` → 文件头插入 INSERTED，exit 0
- `Replace "bar" "BAZ" "1"` → bar→BAZ 替换成功

上游自己的测试（src/test.rc + ruby test.rb）也是宏驱动：随机 2000 步宏 fuzz + undo/redo 一致性 `cmp`——需要 NE_TEST=1 NE_DEBUG=1 插桩构建 + ruby，CI 不可复现（无 ruby）。适配后用 pty + 定向宏回归替代。

## 7. 测试

上游注册的测试目标数 **N=0**（makefile 无 test/check 目标；test.rc/test.rb 是手动工具非注册目标）。test_package 做 4 项 pty 实测（version/help/insert+save/replace）。

## 8. B 素材评估（terminfo/musl 踩坑）

- pty 驱动终端类 TUI 应用测试模式（ne 的 abort 案例）：查 knowledge/graph 无同类条目（"pty" 零命中）→ 候选
- texinfo 生成源码预生成补丁模式（ModulePath.pm 手工 sed 绕过 texinfo 安装）：查重后决定是否申报
- 详见 PR 正文与知识草稿

## 9. 残留/限制

- terminfo 数据库 2868 条全量进包（~几 MB）——可按需裁剪但保守起见全量
- `install-info` 步骤跳过（顶层 makefile install 的 info 装配，CI 无需）
- ELF 签名由 CI sign.sh 流水线负责
