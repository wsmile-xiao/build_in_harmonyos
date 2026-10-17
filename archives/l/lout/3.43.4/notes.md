# lout 3.43.4 适配笔记

## 编译环境
- 构建系统: 单文件非递归 GNU makefile（上游 `makefile`，未重写）
- 编译日期: 2026-09-16
- 编译器: clang 15 (OHOS SDK, `--target=aarch64-linux-ohos`, musl)
- 状态: built
- 目标平台: OpenHarmony / HarmonyOS PC aarch64 (armv8)

## 上游信息

- 软件: Basser Lout — Jeffrey H. Kingston 的文档排版系统
- 3.43.4 官方源码: `https://codeload.github.com/william8000/lout/tar.gz/refs/tags/3.43.4`
- SHA256: `5cc2700f842860dd4d0af95ef5aff8cf9fe1e155d04ee951f790697aa27e7807`
  - 三重验证: 本地构建 tarball、GitHub codeload 实际下载、FreeBSD ports
    `print/lout` distinfo（`william8000-lout-3.43.4_GH0.tar.gz`）一致。
  - Savannah (`download.savannah.gnu.org/releases/lout/`) 与 SourceForge
    (`sourceforge.net/projects/lout/`) 仅托管到 3.40；作者个人主页
    `www.it.usyd.edu.au/~jeff/` 已因大学网站改版失效。3.43.x 的官方
    分发渠道是作者 GitHub 仓库 william8000/lout（FreeBSD ports 为证）。
- 许可证: GPL-2.0-only（源码 `README` 与 `doc/` 声明 "GNU General Public
  Licence, Version 2"）
- 压缩包大小: 1,678,961 字节

## 源码结构

```
lout-3.43.4/
├── README            # 构建/安装说明（含安装后初始化 lout -x 说明）
├── makefile          # 单文件非递归 GNU makefile（编译 52 个 z*.c + 安装 + 测试）
├── z01.c … z52.c     # 排版引擎（lexer/parser/对象系统/断行/页面/后端）
├── prg2lout.c        # 源码 → Lout 文档转换器（独立可执行文件）
├── externs.h         # 全局宏/声明（★ 本任务唯一补丁点）
├── include/          # 标准包定义（doc/report/book/tabl…，即 SysInclude 树）
├── data/             # 预建数据库（.ld/.li/.lh）
├── font/             # 字体度量 + PostScript 字体文件
├── maps/             # 字符映射 .LCM（LtLatin1 等 11 个）
├── hyph/             # 连字规则（.lps + 索引）
├── locale/           # 本地化 message catalog 模板
└── doc/user/         # 用户手册源（无扩展名：all/mybook/bas…）
```

## 上游测试分析（完整盘点）

上游 `make test`（makefile 测试目标，doc/user/Makefile 驱动）的语义：

1. **前置**: `make install` 完成（lout 二进制 + 数据树装入 LOUTLIBDIR），
   并在 doc/user 中有 `user-<OLDVERSION>.ps` 参照文件。
2. **执行**: 用**新编译的 lout** 以 `-r3`（3 遍：正文+索引+交叉引用）
   格式化整本用户手册 `doc/user/all`（约 400 页，80 个章节文件），
   输出 `user.ps`（PS 后端；**上游 `make test` 不跑 plain 后端**）。
3. **对比**: 与旧版本（lout-3.40，`OLDVERSION` 变量）生成的
   `user-<OLDVERSION>.ps` 做 `diff`——排版输出应逐字节一致（验证升级
   不改变输出）；随后调用 `less` 交互查看（README 说明）。

**OHOS 上可运行的部分**: 第 2 步全部（`-r3 all` PS 后端 + `-p -r1 all` plain 后端，
这正是 `make test` 用新二进制执行的实际工作量）；第 3 步 diff 对比需要
lout-3.40 参照二进制，OHOS 无此产物（3.40 无官方 OHOS 构建，且 Savannah
tarball 的 3.40 与 GitHub 3.43.4 数据树存在差异，跨渠道对比无意义），
交互式 less 在 CI 环境不可用。**上游无其他正式测试套件**（无
tests/ 目录、无 run_tests 脚本、无单元测试框架）。

本适配在 conanfile `build()` 中执行可运行核心（L2 阶段）:
- `lout -r3 all -o user.ps`（3 遍 PS 全手册，与上游 `make test` 命令完全一致）
- `lout -p -r1 all -o user.txt`（单遍 plain 全手册，702 KB 完整文本；上游
  `make test` 本不做 plain 后端测试，此处作为补充功能验证，用 `-r1` 的
  原因见下节「-p 多遍截断」）
- 断言 rc==0 且输出非空；user.ps ≈ 4.7 MB / 327 页（与上游发布的手册
  体量一致）、user.txt ≈ 700 KB
- 不带 `-s`（`-s` 是 CH_FLAG_SUPPRESS，会置 `AllowCrossDb=FALSE` 禁用
  交叉引用数据库，恰好废掉 `-r3` 要解析的部分），且每遍运行前清理交叉
  数据库文件 `*.ld *.ldx *.li`（上游 `make test` 同样先
  `rm -f -- *.ld *.ldx *.li`）。

### 上游固有行为: `-p` 纯文本后端多遍运行输出截断（非缺陷引入）

`lout -p -r2 all` 及以上（含 `-r3`）时，plain 输出**只有前页**（title/
preface/contents，约 4 KB），正文章节全部缺失，rc=0 无任何 fatal——而
PS 后端 `-r3` 完整（327 页 4.7 MB），`-p -r1` 也完整（702 KB）。

**证据链**（2026-09-16 复核实验）:
1. 补丁版二进制: `-p -r3` → 4,084 B（只有前页）
2. 未打补丁的原版源码（USELOC=0 编译排除 locale 干扰，catopen 符号
   确认为零）在同一数据树上运行 `-p -r3` → **4,084 B，与补丁版逐字节
   相同**；其 PS 输出与补丁版仅 CreationDate 时间戳不同（内容一致，
   327 页）——排除补丁引入。
3. 机制（z01.c `run()`）: 仅最后一遍打开输出文件（`if( run_num ==
   *runs_to_do )`），前几遍用 NullBackEnd 收集交叉引用数据库；run 2+
   只重读 `all` 等 6 个文件。run 2 中 plain 后端的正文 galley 无法挂接
   （`no @ChapterList galley target`），正文全部被丢弃。
4. 上游手册 str_cros 只承诺多遍正确性针对 PostScript 输出（"a
   perfectly good PostScript file"）；makefile `make test` 也只跑
   PS 后端。

**处理**: 不打补丁（上游设计如此，非 OHOS 适配问题）；L2 的 plain
验证改用 `-p -r1`（完整输出基准）；notes 如实记录。

## 适配过程

### 根因: OHOS musl catgets() 对无效 nl_catd 的处理（SIGSEGV）

**现象**: 编译零错误零警告，但任何排版运行（含最小 hello 文档）立即
`SIGSEGV (rc=-11)`。手工安装树 + `lout -x` 也崩。构建机 glibc 交叉
编译的同一二进制在 glibc 容器中正常。

**定位**（帧指针回溯 + 映射基址换算）: 崩溃帧稳定落在
`catgets(MsgCat, …)` 调用点（z04.c/z10.c 等 30+ 处错误消息宏
`condcatgets` 展开）。OHOS musl 的 `catgets()` 未校验描述符有效性，
直接解引用 `(nl_catd)-1`（0xFFFFFFFFFFFFFFFF）导致段错误。

**根因链**:
1. lout `z01.c` 启动时 `catopen()` 打开 message catalog；OHOS 上该
   catalog 不存在（locale 树未安装）→ 按 POSIX 返回 `(nl_catd)-1`
   哨兵值（不是 NULL）。
2. lout 的宏只判 NULL:
   `#define condcatgets(cat,set,msg,s) (cat ? catgets(cat,set,msg,s) : s)`
   glibc 的 `catgets()` 对无效描述符**容错**（返回 fallback 字符串 `s`），
   所以上游 20 年从未触发；musl 不容错 → 解引用 -1 → SIGSEGV。
3. 上游 3.43 曾对 `catclose()` 打过同类补丁
   (`catclose(cat)` → 先判 `cat != (nl_catd)-1`)，但漏了 `catgets` 路径，
   说明作者已知该哨兵问题，3.43.4 仍未修。

**修复**（patches/0001，externs.h 一处 4 行）: 参照上游自己的
catclose 修复方式，给 condcatgets 加同样的哨兵检查:
```c
#define condcatgets(cat, set, msg, s) \
  ((cat) != (nl_catd)0 && (cat) != (nl_catd)-1 ? catgets(cat, set, msg, s) : s)
```
最小、可解释（POSIX 哨兵语义 + 上游同类先例）、可复现（无补丁必崩 /
有补丁全测试通过）。**未关闭 LOCALE_ON**（保留上游 locale 功能）。

### 其余适配点（无需补丁，配方层解决）

- **CC 注入**: makefile 自带 CFLAGS（-ansi -std=c99 …），唯一工具链注入口是
  `CC` 变量；OHOS 交叉编译器路径 + sysroot 由 profile conf 的
  `tools.build:compiler_executables` 进 CC，一次通过。
- **LIB_DIR 解析顺序**: `$LOUTLIB` > argv[0] 相对 `../../lib` > 编译期
  `LIB_DIR`（默认 /usr/local/share/lout-3.43/lib，不存在）。`-I/-H/-D`
  选项只是**前缀追加**且不覆盖 maps/font 查找路径，所以干净运行必须设
  `LOUTLIB` 指向 res/lib——conanfile 与 test_package 均如此。
- **测试工作目录**: doc/user 的 `all` 通过 `@Include { mybook }` 等**从
  cwd**（非 -I 路径）解析模块文件，且文件无扩展名；测试先复制输入到
  临时目录再运行。
- **z52.c 缺 prg2lout 原型声明**（-Wstrict-prototypes 警告）: 上游已有
  代码风格问题，不影响正确性，不打补丁。

## Conan 包结构

```
package/
├── bin/lout, bin/prg2lout          # 可执行文件
└── res/lib/{include,data,font,     # 运行时数据树（LOUTLIB 指向此处）
             maps,hyph}
```

无 shared 产物（上游无 .so 目标）；无依赖（zlib 可选，默认
PDF_COMPRESSION=0 不启用）。

## 知识库关联

- catgets/(nl_catd)-1 根因 → DRAFT-E577-ohos-musl-catgets-invalid-nl-catd-sentinel
  （新增草稿；检索确认 knowledge/graph 544 条 + drafts 中无 catgets/
  catopen/nl_types 相关条目）

## 验证结果汇总（2026-09-16, ohos-aarch64）

| 检查 | 结果 |
|---|---|
| conan create（含上游测试核心 L2） | ✅ pass — user.ps 4,706,541 B / 327 页（-r3 全量手册 PS 后端）+ user.txt 703,057 B（-p -r1 全量手册 plain 后端） |
| conan test test_package | ✅ pass — 冒烟 2 + 功能 2 + OHOS 专项 4 全过 |
| CI L0（结构/质量门禁） | ✅ pass |
| CI L1（测试执行证据 + 破坏性负测试 R34） | ✅ pass（bin/lib 移走后测试真实失败） |
| CI L2（冒烟） | ✅ pass（lout --version）；⚠️ prg2lout 无 --version 选项——上游设计（无参读 stdin 打 usage），非阻塞 |
| CI L4（补丁危险函数扫描） | ⚠️ warn——正则 `(gets)\b` 误命中 `catgets(`（catgets 含子串 gets），补丁实际不引入任何危险函数，非阻塞 |
| CI L5（产物完整性） | ✅ pass — bin/lout, bin/prg2lout |
| CI JC（junk check, prdiff 模式） | ✅ pass — 单软件合规、无杂项/二进制 |
| CI KC（知识库检查 KC1-KC5） | ✅ pass |
| CI G0（knowledge graph 完整性） | ✅ pass（540 entries） |
| 总 Pass rate | 100% (1/1) |

**shared/static**: 上游无 .so 产物（makefile 唯一链接规则 `lout: $(OBJS)`
纯可执行；`make install` 仅装 bin+数据树），故无 shared 选项——属上游
不支持而非跳过，证据见「适配过程」。

**OHOS conan 行为注意**: 独立 `conan test` 时 settings_build 被强制
Linux/x86_64 → `can_run()` 恒 False → 若用 `if not can_run: return`
门控，test_package 会静默跳过且 L1e 破坏性负测试失效（rc=0 假通过）。
本包 test() 因此**不**用 can_run 门控（test_lout.sh 自身对缺产物快速
失败），此为 L1e/R34 门禁的正确通过方式。

---

**编译结束**: 2026-09-16
**最终状态**: built
