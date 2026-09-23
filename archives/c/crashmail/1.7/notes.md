# crashmail 1.7 适配笔记

## 编译环境

- 构建系统：makefile（上游手写递归 GNU Makefile，`make linux` 目标）
- 编译器：clang 15.0.4（`aarch64-unknown-linux-ohos`，来自 Conan profile `ohos-aarch64`）
- Conan：2.29.1；GNU Make 4.4.1
- 目标：OHOS / HarmonyOS PC aarch64（`os=OHOS` `os.version=6.0` `arch=armv8`）
- 状态：built

## 源码

- 上游正式发行：SourceForge `ftnapps` 项目 `crashmail-1.7.tar.gz`
  （177765 字节，sha256 `fbe5cafa4022c8651c9e97356d4e20540805e535ce1ec28df4d67a45e0233c7d`）
- 本配方实际采用：Debian 官方制品库同源 orig tarball
  （177765 字节，sha256 `3d073b82bd2568fd17bfc8944f1a0a12b5e5e1b3841d43ed6683370084bc1a1c`，
  与 `.dsc` 声明的校验和一致）
- 两者只有 gzip 容器头 mtime 不同，解压载荷逐字节一致：
  sha256 `d6a78777469a822e1e7d8f126f5421cbb0d43848e25b3a4291a2a75d3aa01912`，
  942080 字节，169 个成员，顶层目录 `crashmail-1.7`
- 换成 Debian 镜像的原因：CI worker 出网白名单极窄，`build_and_test.sh` 的
  `get_mirrors()` 对 SourceForge 域直接 `return [url]`（无任何镜像兜底），
  历史实测同域包超时 360s 后失败。逐字节核对已在上方给出。
- conandata.yml 的注释里不写裸 URL：CI 预下载器会无边界抓取 `sources:` 之外的
  URL 并做前缀替换。

## 编译步骤

权威命令记录在 `manifest.yaml` 的 `build.configure_options` 与 `tests.*.command`，
本节只说明流程，不复制命令。

1. `source()`：按 conandata.yml 下载并解压，`strip_root=True` 得到 `crashmail-1.7/`，
   然后 `apply_conandata_patches()`（8 个补丁，日志中应出现 8 条 `Apply patch`）。
2. `generate()`：`AutotoolsToolchain` 只用于生成 conanbuild 环境
   （CC/CFLAGS/CPPFLAGS/LDFLAGS）。上游没有 configure 脚本，不需要额外 flags：
   OHOS clang/lld 默认输出已是 PIE + GNU_RELRO + BIND_NOW + NX。
3. `build()`：先 `make -j1 linux CC_BIN="$CC" STRIP=:`，再在 `tests/` 下启动
   上游 `roundup` 套件。
4. `package()`：`bin/` 下 8 个可执行文件 → `bin/`；`man/*.1` → `share/man/man1/`；
   `doc/*` → `share/doc/crashmail/`；`src/jamlib/LICENSE` → `licenses/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make linux` 用 `clang` 构建时头文件找不到：`'oslib/os.h' file not found` | 四个 Linux makefile 把 `CC` 定义成 `gcc $(CPPFLAGS) $(CFLAGS) $(DEFS) $(LDFLAGS) -I $(INCDIR) -Wall` 的**复合值**；命令行的 `make CC=clang` 会整体替换该定义，同时丢掉 `$(DEFS)` 与 `-I` | 补丁在四个 makefile 中新增 `CC_BIN ?= gcc` 并把 `CC` 改为 `$(CC_BIN) ...`，只重定向编译器本体；配方传 `CC_BIN="$CC"`（编译器来自 Conan 图，R33） |
| 2 | `jamlib/mbase.c` 编译失败：`variable has incomplete type 'struct flock'`、`use of undeclared identifier 'F_SETLK'/'F_WRLCK'/'F_UNLCK'`、`call to undeclared function 'fcntl'` | 该文件在 `#if defined(__LINUX__)` 里只 include 了 `<sys/file.h>` 与 `<unistd.h>`；glibc 的 `<sys/file.h>` 会传递引入 `<fcntl.h>`，musl/OHOS 不会 | 补丁在 `<sys/file.h>` 后显式 `#include <fcntl.h>` |
| 3 | 链接失败：`ld.lld: error: duplicate symbol: lastt`（`pkt.c` 与 `handle.c`） | 两个编译单元各有一份文件作用域试探性定义 `time_t lastt;`，过去靠 GCC<10 默认的 `-fcommon` 静默合体成一个符号（两个模块其实在无意中共享同一个计数器）；clang 15 默认 `-fno-common` | 两处都改成 `static time_t lastt;`（两处调用点都在本文件内，本来就是文件局部计数器） |
| 4 | 构建出的 8 个二进制全部无法执行：`Operation not permitted`，退出码 126 | OHOS lld 在产物中写入 `.codesign` 段，段头第 5 个字段记录被签名镜像的长度（本例 `0x4980` = 18816 = 链接产物字节数）。`strip` 把文件缩小到 10072 字节，签名范围内字节被改动 → 内核拒绝 exec。在文件末尾追加 1 个 **NUL** 字节仍可执行（追加 NUL 不改变签名范围内的内容，只延长文件且不落在签名范围里），可反证判据——注意必须是 NUL：实测追加任何非零字节（0x01/0x20/0x41/0x58/0x7f/0x80/0xff）或截断 1 字节都会得到 126 | 配方传 `STRIP=:` 关闭上游 makefile 的 strip 步骤；`strip` / `llvm-strip` / `strip -g` 三种形态实测均失效，不能用于 OHOS 产物 |
| 5 | `tests/roundup` 无法启动：`/bin/bash: bad interpreter: No such file or directory` | 上游 test runner 的 shebang 是 `#!/bin/bash`，OHOS 上 bash 位于 `/data/service/hnp/bin/bash`，没有 `/bin/bash` | 配方/测试脚本用 PATH 与 `CONFIG_SHELL` 解析出的 bash 显式启动同一套件，**未改动任何上游测试用例** |
| 6 | CI worker 上 `tests/roundup` 启动即失败：`mktemp: need XXXXXX: Not supported`（退出码 1，一条用例都没跑到） | `tests/roundup:88` 用的是 `mktemp -d -t .roundup.XXX`（**3 个 X**）。GNU coreutils 的 mktemp 接受 ≥3 个 X，toybox 的 mktemp **要求恰好 6 个 X**，否则报 `need XXXXXX: Not supported` 并返回 1。设备上 PATH 命中的是 coreutils 的 `mktemp`（GNU 9.10，随用户级工具链安装，位置随执行机而异）故本地全绿；CI worker 上没有该副本，`mktemp` 解析到 toybox 即失败——设备全绿 ≠ CI 绿 | 补丁 `0008-tests-roundup.patch` 把模板从 `.roundup.XXX` 加宽为 `.roundup.XXXXXX`（**单 token 改动，不触及任何用例、断言或测试逻辑**）。A/B 实测：把 toybox mktemp 置于 PATH 首位，未打补丁时 rc=1 且报同一条错，打补丁后 18/18 PASS、rc=0 |
| 7 | CI worker 上 `test_package` 的 A7 假失败：`areas/netmail/2.msg 不含投递的主题`（A1–A6 全绿，设备侧同轮全绿） | A7 用 `grep -q '<主题>' areas/netmail/2.msg` 检查投递结果，而 `*.msg` 是**定长头 + NUL 填充的二进制格式**。**toybox 的 grep 不在含 NUL 的二进制文件里匹配**（字符串确实存在也返回 1，`-a` 同样无效）；coreutils 的 grep 会返回 0。设备 PATH 命中的是 coreutils grep，CI worker 上解析到 toybox grep → 假失败 | 测试侧改为先 `tr -d '\000' < areas/netmail/2.msg` 把内容变成文本流再 `grep -q`，该写法在 toybox 与 coreutils 两套工具链下均实测通过。A/B 实测：把 toybox 的 grep/tr/od/diff 置于 PATH 首位复刻 worker，**旧写法 rc=1 且报错与 CI 逐字相同，新写法 8/8 PASS、rc=0** |

## 源码修改

8 个补丁，与 `conandata.yml` 的 `patches` 一一对应：

| 补丁 | 修改内容 | 类型 |
|------|----------|------|
| `0001-src-Makefile.linux.patch` | 新增 `CC_BIN ?= gcc`，`CC` 改为 `$(CC_BIN) ...` | portability |
| `0002-src-cmnllib-Makefile.linux.patch` | 同上（cmnllib） | portability |
| `0005-src-jamlib-Makefile.linux.patch` | 同上（jamlib） | portability |
| `0007-src-oslib_linux-Makefile.patch` | 同上（oslib_linux） | portability |
| `0006-src-jamlib-mbase.c.patch` | `__LINUX__` 分支补 `#include <fcntl.h>` | portability |
| `0003-src-crashmail-handle.c.patch` | `time_t lastt;` → `static time_t lastt;` | bugfix |
| `0004-src-crashmail-pkt.c.patch` | `time_t lastt;` → `static time_t lastt;` | bugfix |
| `0008-tests-roundup.patch` | `tests/roundup` 的 mktemp 模板 `.roundup.XXX` → `.roundup.XXXXXX` | portability |

7 个补丁落在 `src/`（构建与可移植性）；第 8 个是**唯一触及 `tests/` 的补丁**，
只改 roundup 运行器创建临时目录的模板（`.XXX` → `.XXXXXX`），
**不修改任何测试用例、断言或测试逻辑**，18 个 `it_*` 用例原样执行。
`test_package/data/` 下的 6 个夹具文件逐字节复制自上游 `tests/`
（nodelist.txt、pointlist.txt、cmnodelist.prefs、crashmail.prefs、
crashgetnode-node.expected、crashgetnode-point.expected）。

## 依赖版本

无编译依赖、无运行依赖。`DT_NEEDED` 只有 `libc.so`。

## 验证结果

取数口径与命令见 `manifest.yaml` 的 `tests.upstream.command` /
`tests.upstream.total` / `tests.test_package.*`；判据与全部数字的复算方式见
`reports/conan-verify-supplement.md`（含采信轮日志的 sha256、字节数、行数与
各标记计数）。原始 `conan-create.log` **不入库**（`*.log` 属 review-memory §19
的 PR 禁止入库类型，且日志含本机绝对路径），按 workflow §7.2 留在仓库外，
用 sha256 锚定身份即可复核。

- 上游测试：`Tests:    18 | Passed:   18 | Skipped:   0 | Failed:    0`
  （统计单位 = roundup 的 `it_*` 用例；5 个 test plan：
  nodelist 3、crashwrite 1、crashmail 6、crashstats 6、areafix 2）
- `test_package`：8 条断言全部通过（A1 版本指纹、A2 nodelist 索引、
  A3/A4 crashgetnode 逐字节比对、A5 type-2+ 包 magic `0200`、A6 toss 报告、
  A7 投递结果内容、A8 crashstats 输出）
- 安全属性：`Type: DYN`（PIE）+ `GNU_RELRO` + `FLAGS: BIND_NOW` +
  `GNU_STACK RW`（NX）

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/crashmail` | 主程序 |
| `bin/crashwrite` | 生成入站包 |
| `bin/crashlist` | nodelist 索引 |
| `bin/crashgetnode` | 4D 地址查询 |
| `bin/crashstats` | 统计输出 |
| `bin/crashlistout` | 节点清单输出 |
| `bin/crashmaint` | JAM 消息库维护 |
| `bin/crashexport` | 包导出为文本 |
| `share/man/man1/*.1` | 8 个 man 手册 |
| `share/doc/crashmail/*` | `example.prefs`（配置关键字文档）、`ReadMe.txt`、`AreafixHelp.txt`、`filter.txt` |
| `licenses/LICENSE` | JAMLIB 的 LGPL-2.1 文本 |

## 注意事项

- 不要对 OHOS 产物做 `strip` / `objcopy` / 重新签名：`.codesign` 段校验的是
  签名范围内的字节，任何改写都会让文件变成不可执行（退出码 126，无更多提示）。
  判据是「退出码不是 126」而不是「退出码为 0」——成功加载的程序在缺参数时
  会打印各自的用法信息并按用法约定返回非零码（本包实测为 10 或 0）。
- **`bin/crashmail` 逐轮不可复现**：`src/crashmail/crashmail.c:321-322` 无条件
  内嵌 `__DATE__`/`__TIME__`（`printf("Compilation date: %s\n",__DATE__);`），
  故每次构建的 sha256 都不同（`strings` 可核对到编译日期与时间字面量）。
  其余 7 个产物不含该宏，四轮独立清缓存干净构建逐字节一致。做产物基线对比时
  应以那 7 个为可复现子集，详见 `reports/conan-verify-supplement.md`。
- 本包不产出 `.so`，`package_info()` 的 `libdirs`/`includedirs` 均为空，
  消费方式是把 `bin/` 加到 PATH。
- `crashmail` 需要一个 prefs 配置文件才能运行；配置关键字文档随包安装到
  `share/doc/crashmail/example.prefs`。
