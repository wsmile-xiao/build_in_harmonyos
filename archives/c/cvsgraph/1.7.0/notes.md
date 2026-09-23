# cvsgraph 1.7.0 适配笔记

## CI 修复轮 2（2026-09-15，PR #10072 构建 #47890 → 依赖切换）

**进展**：#47890（CI-032）上构建全绿（编译/链接/打包），--host cross
降级完美工作（configure 全过、gd 全特性 yes）；**新失败在 test_package
运行期**：

```
Error loading shared library /storage/Users/currentUser/.conan2/p/expat.../lib/libexpat.so
(needed by .../.cache/conan2/p/fontc.../libfontconfig.so.1)
```

**根因（ELF 解析实证）**：ohpcd 已发布的 fontconfig/2.18.1 二进制
libfontconfig.so.1.17.0 对 libexpat 的 DT_NEEDED 是**烤死的绝对路径**
`/storage/Users/currentUser/.conan2/p/expat9fb72708ad085/p/lib/libexpat.so`
（构建机缓存在 $HOME/.conan2；包哈希目录跨机确定性同名）。加载器对绝对
DT_NEEDED 不搜索，LD_LIBRARY_PATH 无效。**真机全绿是侥幸**——设备主
缓存恰好有同哈希目录；CI 缓存在 .cache/conan2 必挂。同闭包 libgd 对
libexpat 是裸 soname（正常），仅 fontconfig 烤了路径。

**修复**：依赖 **gd/2.3.3.1 → gd/2.3.3**（static 变体，zlib+libpng；
libpng16.so.16 实证仅 NEEDED libc.so）。运行期闭包缩到 libpng16.so.16
+ libc，整类问题消灭。代价：TTF 不可用（HAVE_GD_STRINGFT 不定义），
cvsgraph 用 gd 内置位图字体（上游默认 use_ttf=false 本就不依赖 TTF；
PNG 输出满足 cvsgraph.c 的硬性要求）。知识草稿
`cvsgraph-1.7.0-fontconfig-baked-abs-dt-needed.*` 已沉淀检测法与判别
口诀（**DT_NEEDED 含 '/' 即烤死路径，推送前查，别等 CI 揭盲盒**）。

**根治待办（另行立项，勿混入本 PR）**：重编 fontconfig 修 soname 后以
R37 后缀版本重发 ohpcd；graphviz 等其他 gd/2.3.3.1 消费者同受影响。

## CI 修复轮（2026-09-15，PR #10072 构建 #47863 → 修复）

**失败**：`checking whether the C compiler works... configure: error: cannot
run C compiled programs`——与真机首败同症状，但 LD_LIBRARY_PATH 已注入
（RUN 行可见 gd 目录在列）仍失败。

**根因**：CI worker 沙箱**禁止运行 conftest 可执行文件**（cadaver #30663
先例实证，speex 同；症状逐字相同）。真机能跑通是因为交互会话不受限。
真机与 CI 的 ohos-aarch64 profile 相同（CONFIG_SHELL=hnp bash、
LD_LIBRARY_PATH=llvm/lib），差异只在 worker 沙箱策略。

**修复**（两处，均已提交）：
1. configure 加 `--host=aarch64-linux-ohos`（不带 --build）——autoconf
   2.5x 的官方 cross 触发器：host_alias 非空且 build_alias 空 →
   `cross_compiling=maybe`（configure L1130，无 AC_CANONICAL_HOST 也生效）。
   conftest 可运行（真机）→ 通过保持 no 全真实检测；被沙箱拦截（CI）→
   自动降级 cross=yes 继续，AC_CHECK_LIB 链接探测不受影响。CC 由工具链
   环境显式指定，ac_tool_prefix 前缀查找不参与；memset/strdup/strtol
   cross 模式缺 HAVE_ 宏但源码零守卫（libc 直接提供），无害。
   **注意：此前"不传 --host"的判断是错的**——2.5x 的 --host 并非"解析
   但完全不用"，它是 cross_compiling 的唯一开关；知识草稿已更正。
2. LD_LIBRARY_PATH 改**追加**语义（`:$LD_LIBRARY_PATH`）——CI lld 依赖
   profile 注入的 llvm/lib 下 libxml2.so.16，替换语义在部分 worker 上
   会弄挂链接（ohos-ci-environment-issues 记录的已知环境差异）。

**无效路径备忘**：`ac_cv_prog_cc_works=yes`（2.61 works 检查不读该缓存
变量，cadaver 的 VAR=value 路线只适用 2.6x+ 生成物）；替换 LD_LIBRARY_PATH
（本例 #47863 中链接已通过、运行仍失败，证明主因是沙箱而非库路径）。

## 真机验证结果（2026-09-14，设备 10.62.178.77，全部通过 ✅）

- `conan create archives/c/cvsgraph/1.7.0 -pr:h ohos-aarch64 -pr:b ohos-aarch64
  -r ohpcd --build=missing` → **RC=0**（隔离 CONAN_HOME=`$HOME/tmp/cvsgraph-conan-home`，
  jobs=1，全程 MemAvailable ≥12GB）
- test_package 双用例通过：`-V` 输出 `cvsgraph v1.7.0`；最小 RCS 文件渲染出
  1640 字节合法 PNG（魔数 `89 50 4e 47 0d 0a 1a 0a`）
- 包布局：`bin/cvsgraph` + `share/man/man1/cvsgraph.1` + `share/man/man5/cvsgraph.conf.5`
- config.h 全 9 个 HAVE_GD* 宏（PNG/JPEG/GIF/PNGEX/STRINGFT/FILLEDARC 齐全），
  AC_CHECK_FUNCS 真实运行检测全过

## 真机排障记录（4 轮迭代，新坑全部沉淀）

| # | 现象 | 根因 | 解决 |
|---|------|------|------|
| 1 | configure 启动即大量 `shell-init: error retrieving current directory: getcwd` 噪音，中止于 `configure: error: Working directory cannot be determined` | `/data/service/hnp/bin/bash` 在 conan 构建(HMDFS 深)目录里 getcwd 损坏（E386 的"shell 可返回 0 但带诊断"情形）；同目录 `/system/bin/sh` 探针干净 | configure 改用 `/system/bin/sh` 显式调用 + `CONFIG_SHELL=/system/bin/sh`（防 autoconf 把 hnp bash 烤进 Makefile 的 SHELL） |
| 2 | `checking whether the C compiler works... configure: error: cannot run C compiled programs` | 无 AC_CANONICAL_HOST → cross_compiling 恒 no → configure 真实运行 conftest；conftest 链接了 AutotoolsDeps 注入的 `-lgd`，运行期无 LD_LIBRARY_PATH → `Error loading shared library libgd.so.3`。**不是** XPM 签名/noexec | 从 `conanautotoolsdeps.sh` 提取 -L 目录，**内联**在 configure 命令前缀注入 LD_LIBRARY_PATH。⚠️ 不能用 Environment().define：`env="conanbuild"` 会 source conanbuildenv-*.sh，其 export 会覆盖外层值 |
| 3 | 正则 `-L(\S+)` 把 shell 文件行尾引号吃进路径 → `/system/bin/sh: no closing quote` | conanautotoolsdeps.sh 的 LDFLAGS 行以 `"` 结尾，\S+ 吞引号 | 改 `-L([^\s"]+)` |
| 4 | 包内出现 `storage/` 嵌套目录（无 bin/） | 本 conan 发行版 Autotools.install() 自动注入 `DESTDIR=package_folder` 且 AutotoolsToolchain 默认 `prefix="/"`；我手动传绝对 `--prefix=<package_folder>` 与 DESTDIR 双叠 | 手动 configure 一律 `--prefix=/`（fcrackzip 同款） |
| 5 | test_package `cvsgraph -V` 报 127；`self.cpp.build.bindirs` 为空 IndexError | 此 conan 的 conanrun PATH 只含依赖 bindir，不含被测包自身 bin/；cpp.build.bindirs 仅当 test_package 自建产物时非空（cdb/clips 是自建测试程序的场景） | `self.dependencies[self.tested_reference_str].package_folder` + `bin/cvsgraph` 显式路径 |

辅助事实：`ac_cv_prog_cc_works=yes` cache 变量在此 autoconf 2.61 生成物上
**无效**（works 检查不走该缓存变量，cadaver #6257 场景不适用）——真跑通
LD_LIBRARY_PATH 后运行检测自然全过，无需任何 cache 造假。

## W0 依赖检查（2026-09-12，本机实测）

| 依赖 | 制品仓状态 | 证据 |
|------|-----------|------|
| gd/2.3.3.1（选定，shared，PNG+FreeType 全功能） | ✅ recipe + 二进制 | `conan download "gd/2.3.3.1" -r=ohpcd` 成功，options `shared: True`，依赖闭包 fontconfig/freetype/libjpeg-turbo/libpng/libtiff/libwebp/zlib 齐全 |
| gd/2.3.3（最小版 zlib+libpng，无 freetype） | ✅ 已发布 | 未采用：cvsgraph.c:55 要求 GIF/PNG/JPEG 至少其一（PNG 可满足），但 TTF 渲染走 gdImageStringFT，选 2.3.3.1 保完整功能 |
| 其余 | 无 | 纯 C，仅 libm（musl 内置）；lex/yacc 见下 |

## 源码与构建系统分析

- 官方源：`https://www.vagrearg.org/cvsgraph/release/cvsgraph-1.7.0.tar.gz`
  （作者 Bertho Stuijt 站点；SourceForge `downloads.sourceforge.net/project/cvsgraph/...` 实测 404/403，主页直接链到 vagrearg.org 的 release 目录）
- SHA256：`74438faaefd325c7a8ed289ea5d1657befe1d1859d55f8fbbcc7452f4efd435f`（202678 字节）
- 构建系统：autotools（autoconf 2.61 时代 configure.in）
- **无 AC_CANONICAL_HOST**：无交叉三元组、tarball 不带 config.guess/config.sub。
  交叉编译完全由 Conan 工具链环境变量（CC/CFLAGS 等）驱动；configure 认识
  --host 选项但不会用它做任何事 → 不传（R1 只传 --prefix）
- **lex/yacc**：AC_PROG_LEX/AC_PROG_YACC 存在，但 tarball 自带预生成
  rcsl.c/rcsy.c/rcsy.h 且 mtime 晚于 rcsl.l/rcsy.y（2008-05-22 05:24 >
  2008-05-22 03:02 / 2005-08-30）→ make 不会重新生成。configure 缺 lex 时
  置 `LEX=":"` 不硬失败。recipe 里加防御性 mtime 断言（不修改内容）
- gd 探测：configure 先找 gdlib-config（gd conan 包不含，bin/ 里只有
  annotate/webpng 等工具），否则 --with-gd=DIR。两者都不需要：
  AutotoolsDeps 把 gd/freetype 的 -I/-L/-l 注入环境后，
  AC_CHECK_LIB(gd, gdImageCreate/gdImagePng/gdImageStringFT...) 与
  AC_CHECK_LIB(freetype, FT_Load_Glyph) 全部通过（链接共享 libgd.so，
  其 DT_NEEDED 自带 png/freetype 等闭包）
- `bin_PROGRAMS = cvsgraph` → CLI 工具，软件级目录有 commands.json（R38）
- AM_CFLAGS 烤入 `-DETCDIR='"${sysconfdir}"'`：默认配置文件路径
  $prefix/etc/cvsgraph.conf，无碍

## 上游测试清点（R51）

**上游无测试套件**。证据：
1. Makefile.am 无 `check:`/`TESTS` 定义（grep 实测 0 命中），automake 默认
   check 目标为空操作；
2. tarball 无 tests/ 目录；
3. `make check` 上游等价于无操作，不构成可裁剪项。

## 本机已完成的验证

- 源码 URL 可达 + sha256 计算 ✅
- `python -m py_compile conanfile.py test_package/conanfile.py` ✅（见下）
- `conan inspect` 解析配方 ✅（name/version/package_type=application/settings 四项）
- pre-commit hook（ci/conan/hooks/pre-commit，L0a-L0n 等效）**全部通过** ✅
- preflight PF1-PF9：PF1-PF8+R52 全过；**PF9 唯一命中为已知误报**——
  R38 要求 CLI 包在软件级目录（archives/c/cvsgraph/）放 commands.json，
  PF9 的"缺版本目录层"规则对这类文件无豁免，二者框架级冲突。
  先例：clips #8948、cdb #8907、dime #9716 等 CLI PR 均以
  `--no-preflight` 提交且已合并（本仓 2026-09 后所有含 commands.json 的
  CLI 包同此形态）。创建 PR 时按先例用 `--no-preflight`，并在 PR 描述注明。
- W0 依赖发布检查（conan download 实证）✅
- RCS 测试文件按 rcsy.y 语法核对（admin: head/branch/access/symbols/locks/
  strict/comment；delta: date/author/state/branches/next；desc；
  dtexts 可选且 parse_logs 默认 false 提前返回）✅
- 上游 cvsgraph.conf 关键项核对：`use_ttf = false`（166 行，无需字体文件）、
  `image_type = png`（448 行）、`cvsroot = "/var/cvs"`（测试用 `-r ""` 覆盖）✅

## 真机/CI 后续（真机已过，剩 shadow CI）

真机 conan create + test_package 已全绿（见顶部结果）。剩余：

```sh
# shadow CI（单包，等 CI 窗口）
CI_PACKAGES="archives/c/cvsgraph/1.7.0" zsh ci/conan/build_and_test.sh
# 或运行器：/path/to/run-ohos-shadow-ci.sh archives/c/cvsgraph/1.7.0

# 真机复验（如需）
ssh -T -p 2222 -i ~/.ssh/id_rsa currentUser@10.62.178.77
#   隔离 home: $HOME/tmp/cvsgraph-conan-home（ohpcd remote 已补）
#   离线源:   $HOME/tmp/cvsgraph-dl/s/74438faa...（sha256 校验通过）
#   验证仓:   $HOME/build_in_harmonyos（配方文件已就位）
```

## 原预期风险点（真机实测全部化解）

| # | 原风险 | 实际结果 |
|---|--------|----------|
| 1 | bash 依赖 | **反转**：hnp bash 在构建目录 getcwd 损坏，改用 /system/bin/sh（见排障 #1） |
| 2 | 误探 bare ld | 未发生（无 libtool/AC_PROG_LD，无需 ld 符号链接） |
| 3 | hmdfs exec / mksh | 显式 sh 调用规避 ✓ |
| 4 | make -j1 | 已固定，无问题 |
| 5 | libgd.so 运行期解析 | conanrun LD_LIBRARY_PATH 正常；但 configure conftest 需配方注入（排障 #2） |
| 6 | RCS 测试文件 | 一次通过，无需降级 |

## 依赖版本

- gd/2.3.3（static，zlib+libpng；2026-09-15 由 2.3.3.1 切换，原因见顶部"CI 修复轮 2"）

## 版本号

首次适配上游 1.7.0 → 版本号 `1.7.0`（R37，无适配后缀）
