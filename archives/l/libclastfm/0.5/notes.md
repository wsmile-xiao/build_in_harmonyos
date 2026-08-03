# libclastfm 0.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-28
- 编译器: clang/clang++ (OHOS SDK)
- 状态: built (本地真机预检通过后由 HMBS 推送并标 published)
- 源码 URL: https://downloads.sourceforge.net/project/liblastfm/libclastfm-0.5.tar.gz
- 源码 sha256: c9aa7817b557f8d8ef834755740fc813f9351f3185b5bdf4de249bee3675ee42
- License: GPL-3.0-only
- 上游主页: https://liblastfm.sourceforge.net/

## 软件说明

libclastfm 是 Vikram Ambrose 2009 年编写的非官方 Last.fm C API，目的是在官方 Qt 库之外提供一个干净的 C 实现。所有 HTTP 流量走 libcurl 到 `http://ws.audioscrobbler.com/2.0/`。提供 album/artist/user/track/tag 等服务的纯 C 接口，产物是 `libclastfm.la`（库），无命令行二进制。

## 依赖

- `libcurl`（cmd-pkgs 预编译包 `curl 8.19.0`，装到 `$DEFAULT_PREFIX`）— 上游 `configure.ac` 用 `PKG_CHECK_MODULES(CURL, libcurl)`，`src/Makefile.am` 链接 `$(CURL_LIBS)`。**制品仓 ohpcd remote 不分发 curl conan 包**（两轮真机预检均报 `Unable to find 'curl/...' in remotes`，curl 8.5.0 仅仓库自标 published 未 upload、curl 8.15.0 仅 built；conancenter remote 在 CI 被 disable），故仿 curlpp 0.8.1 / bibtexconv 2.2.2 / lastpass-cli 1.6.1 范式：在 `generate()` 用 `cmd-pkgs install.sh` 装 curl 预编译包到 prefix，设 `PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig` + `-I$PREFIX/include` + `-L$PREFIX/lib` 喐给上游 `PKG_CHECK_MODULES`。cmd-pkgs curl 8.19.0 含 `curl/curl.h` 头 + `lib/pkgconfig/libcurl.pc`。
- libclastfm 不是系统同名库，默认静态 (`--enable-static --disable-shared`) 以避免鸿蒙 RPATH 不稳定 (R26 同源考虑)。

## 编译步骤（真机/HMBS 预检环境）

```bash
# HMBS 注入的环境：SHELL=/bin/sh、TMPDIR/TMP/TEMP、HMBS_CMAKE/MAKE/NINJA/PYTHON3、
# tools.build:jobs=1、HMBS_CAP_HARDLINK/CHMOD/SYMLINK/LOCAL_MKTEMP 等。
export TMPDIR=${TMPDIR:-$HOME/tmp}
mkdir -p "$TMPDIR"

cd libclastfm-0.5
# 0001-configure.patch 已由 conanfile.py apply_conandata_patches 应用
./configure --prefix=$DEFAULT_PREFIX --enable-static --disable-shared
make -j1
make install
```

`make check` 不存在有效 target：顶层 `Makefile.am` 无 `check` 目标，`src/Makefile.am` 只把 `test`/`example` 列为 `noinst_PROGRAMS`（构建不运行）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot create temp dir `./confXXXXXX`: Permission denied | HMDFS: `umask 077 && mktemp -d "./confXXXXXX"` 创建目录权限 070、owner UID 为 HMDFS 元数据 UID（20001006），进程 UID（20020082）无写权限，chmod 也无效（E046） | 补丁 `0001-configure.patch`：改用 `${TMPDIR:-$HOME/tmp}/confXXXXXX` 并去掉 `umask 077`，目录获得组可写权限 (drwxrws--x)。参考 sipcalc 1.1.6 同模式 (E011)。 |
| 2 | configure: could not find libcurl | OHOS 环境无系统 libcurl；制品仓 ohpcd remote 不分发 curl conan 包（两轮预检 `Unable to find 'curl/...' in remotes`），conancenter 在 CI 被 disable | `generate()` 用 `cmd-pkgs install.sh` 装 curl 8.19.0 预编译包到 `$DEFAULT_PREFIX`，设 `PKG_CONFIG_PATH` + `-I` + `-L` 喐给上游 `PKG_CHECK_MODULES(CURL,libcurl)`。参考 curlpp 0.8.1 / bibtexconv 2.2.2。 |
| 3 | `tc.environment.define("PKG_CONFIG_PATH", ...)` → `AttributeError: 'function' object has no attribute 'define'` | 真机 conan 2.30 的 `AutotoolsToolchain.environment` 是方法不是对象，`.define()` API 不存在 | 改用 `os.environ["PKG_CONFIG_PATH"] = ...` / `os.environ["TMPDIR"] = ...` 范式（cf. autocutsel 0.10.1、coinutils 2.11.13、ffmpeg）。configure 子进程继承 os.environ。 |
| 4 | `config.guess: line 1337: .../tmp/cgoDbifK/dummy.c: Permission denied` → `unable to guess system type` → `configure: error: cannot guess build type` | 上游 config.guess 是 2012-02-10 版本，(a) 不认 `uname -s = HarmonyOS`，(b) 在 HMDFS tmp 目录建 dummy.c 编译探测时权限拒绝 | `tc.configure_args.append("--build=aarch64-unknown-linux-gnu")` 显式指定 build triplet，configure 跳过 config.guess 完全不运行（E007）。参考 bash 5.3 / bmon 4.0 / berkeley-db 4.8.30 / dateutils 0.4.11。config.sub (2012) 接受 aarch64-unknown-linux-gnu 标准 triplet。 |
| 5 | `conan build 目录 pwd 报错` | HMDFS 上 conan 创建的 build tree 父路径链断裂，`pwd`/`getcwd()` 失败 | build() 开头 `os.chdir(build_folder); os.environ["PWD"]=build_folder`，参考 sipcalc 1.1.6。 |
| 6 | `checking for CURL... no` → `configure: error: Could not find libcurl`（pkg-config 找到了 `/data/service/hnp/bin/pkg-config` 但 PKG_CONFIG_PATH 没真传进 configure 子进程） | conan `Autotools.configure()` 跑 configure 时套用的是 generate() 阶段产出的聚合 `conanbuild.sh`，build() 里对 `os.environ` 的改动会被它 shadow（ffmpeg 4.4.8 notes 实测："仅设 os.environ 时 configure 报 'opus not found using pkg-config'，而命令行内联 `PKG_CONFIG_PATH=... pkg-config` 是 rc=0"） | 改用 dfu-programmer 1.1.0 范式：把 `PKG_CONFIG_PATH=...` 当 configure_args 直接传（autotools 接受 `VAR=value` 形式的环境赋值参数，configure 命令行上的 env-var assignment 会转发给 pkg-config 探测）。同时加 `CURL_CFLAGS=-I$prefix/include` + `CURL_LIBS="-L$prefix/lib -lcurl"` 兜底，short-circuit configure.ac 的 `PKG_CHECK_MODULES` 探测。 |
| 7 | `./config.status: line 712: print: command not found` × 一堆 + `../libtool: line 350: syntax error near unexpected token '}'` → `echo "local: *; };" >> $output_objdir/$libname.ver~` → `make: *** [Makefile:378] Error 2` | HarmonyOS 默认 toybox 工具链（sed/expr/print）：autotools 生成的 libtool/config.status 大量用 GNU 扩展——多行命令块 `{...}`、libtool 的 `>>file~` 后缀、`print -r` builtin。toybox sed 不认多行块就吐 libtool 语法错误，toybox print 不是外部命令就 `command not found`（E010）。真机日志 `checking for a sed... /system/bin/sed`（toybox）坐实。 | E010 范式：`generate()` 用 `cmd-pkgs install.sh` 装 GNU sed 4.9 + coreutils 9.10 到 `$DEFAULT_PREFIX`，把 `$prefix/bin` 前置 PATH，并通过 `tc.configure_args.append("PATH=...")` 传给 configure 子进程（同 #6 的 conanbuild.sh shadow 坑，光设 os.environ 不够）。configure 产出的 libtool/Makefile/config.status 全把 `sed`/`expr`/`print` 解析到 GNU 二进制。 |
| 8 | `../libtool: line 350: syntax error near unexpected token '}'`（GNU sed 装好后仍报）→ `echo "local: *; };" >> $output_objdir/$libname.ver~` | libtool 2.4.2（上游 ltmain.sh）用 `~` 作 lazy-eval 命令分隔符（ltmain.sh:1306 注释「Execute tilde-delimited COMMANDS」）：`archive_expsym_cmds='echo ... >> $libname.ver~ cat ...~'`、`eval cmds="$cmds~$RM $delfiles"`、`concat_cmds=$concat_cmds~`、`IFS='~'` split。HarmonyOS bash 把未引用 `~` 当 tilde expansion 吃掉 → `syntax error near unexpected token '}'`（`}` 来自下一行 `echo "local: *; };"`）。E010 的 GNU sed 装包只治多行块，治不了这个 `~` 分隔语法。 | `build()` 里 `autotools.configure()` 跑完后用 `replace_in_file` 改产出的 `libtool`：把 `IFS='~'` 换 `IFS=$'\n'`、`>> $libname.ver~`/`>> $lib.exp~`/`$cmds~`/`$concat_cmds~`/`${concat_cmds}~`/`concat_cmds=$concat_cmds~` 换真换行符 `\n`。`func_execute_cmds` 的 IFS split 改用换行分隔，bash eval 时换行是合法命令分隔且 `echo "local: *; };"` 引号内的 `;` 不受影响。范式参考 libgcrypt 1.12.2（同样用 replace_in_file 改 instantiated libtool）。不动正则字符类 `[\[~#^...]` 里的 `~`（那是合法元字符）。**踩坑**：① 第二条 pattern 初版误抄 `IFS="$IFS"; IFS='~'`（漏 `save_` 前缀，真模板是 `save_ifs="$IFS"; IFS='~'`）→ `replace_in_file didn't find pattern` ConanException 整停；② 所有 `replace_in_file` 必须加 `strict=False`（bmon 4.0 范式），否则某条 pattern 在 ltmain 实例化后不在 libtool 出现就硬 throw 整停 build；③ **replacement 不能用 `;`**——会跟 `echo "local: *; };"` 字串内的 `;` 冲突，bash eval 整串时把字串内 `;` 误当命令分隔提前执行 `echo "local: *"`，再看到 `}"` 仍报 `syntax error near unexpected token '}'`（真机第 10 轮实测坐实）。libtool 2.4.2 用 `~` 分隔本就是为避免跟字串内 `;` 冲突，换 `\n` 真换行符才两全。**④ 即使 `~`→`\n` 生效（真机第 11 轮报错串末尾已无 `~`/`;`），bash 仍报 `syntax error near unexpected token '}'`**——真根是 `archive_expsym_cmds` 串第 3 条 `echo "local: *; };"` 被 `func_execute_cmds` 的 `eval cmd="$cmd"` 二次展开时吃掉一层引号，裸 `}` 触发 bash brace expansion 错误。这条在 dash/mksh 下合法（无 brace expansion），bash 5.x 报错——libtool 2.4.2 设计依赖 dash/mksh 语义。**治根**：用 Python `re.sub` 把 libtool 里 `archive_expsym_cmds='...'` 和 `module_expsym_cmds='...'` 整条单引号多行赋值置空（`archive_expsym_cmds=''\n`），让 ltmain.sh:8516 `test -n "$archive_expsym_cmds"` 失败，libtool 退回 `archive_cmds`（static 库正常路径，不含 `echo "local: *; };"`）。本轮 build `--disable-shared` 本就该走 archive_cmds，export_symbols 是误探测。 |

## 源码修改

### configure (1 file modified)

- **修改内容**: 将 `mktemp -d "./confXXXXXX"` 改为 `mktemp -d "${TMPDIR:-$HOME/tmp}/confXXXXXX"`，并移除 `umask 077`；fallback 分支同理改用 `${TMPDIR:-$HOME/tmp}`。
- **修改原因**: HMDFS 文件系统中，`umask 077` 创建的临时目录权限为 070、owner 为 HMDFS 元数据 UID，与运行进程 UID 不一致，无写权限；chmod 亦无效（E046）。改用 `$TMPDIR`（不在 HMDFS 挂载点）并去掉 `umask 077` 使目录获得组可写权限。
- **补丁状态**: `patches/0001-configure.patch`，由 conandata.yml 声明，conanfile.py `apply_conandata_patches()` 应用。

## 上游测试审计

上游 `src/test.c` 定义 5 个 Last.fm API 集成测试：

| # | 函数 | API | 验证 |
|---|------|-----|------|
| 1 | `test_artist_get_info` | `artist.getInfo` | 拉取 Cher 艺术家信息并比对字段 |
| 2 | `test_album_get_info` | `album.getInfo` | 拉取 Air/Moon Safari 专辑信息并比对 |
| 3 | `test_album_search` | `album.search` | 搜索 "believe" 专辑，比对前 4 结果与页数 |
| 4 | `test_track_get_similar` | `track.getSimilar` | 拿 believe/cher 相似曲目列表 |
| 5 | `test_user_get_recent_tracks` | `user.getRecentTracks` | 拿用户 rj 的最近曲目 |

**无法在真机/CI 执行的根因**：
1. `main(argc, argv)` 要求 `argv[1]=API_KEY`、`argv[2]=API_SECRET`（Last.fm 个人开发者凭据，32 字符 secret），无凭据直接 `return 1`。
2. 5 个测试全部直连 `http://ws.audioscrobbler.com/2.0/`，依赖外网与 Last.fm 服务器实时响应。
3. HMBS 真机预检环境与 CI worker 均为隔离环境，无外网、无凭据；mock 不可行——库无 test harness，`lastfm.c` 直用 curl 发 HTTP，断言比对的是服务器返回的活数据。

**处理**：按守则在 `test_package/MANIFEST.yml` 如实声明 `upstream_tests_exist: true`、`discovered: 5`、`executed: 0`、`status: "skipped"` + reason；HMBS 标记输出同样数字。PR 正文「上游测试通过率」填 `0/5（0%）`，紧接列未运行用例与原因；补充说明写明定语。

**离线补齐尝试结论**：守则要求「先尝试低成本补齐」。已评估两条均不可行：
- vendor GTest 等是另一类问题；此处 5 个测试本不是 GTest，是手写 main + curl。
- 离线小数据集替代不可行：测试代码直接调用 `LASTFM_album_get_info(s,"air","moon safari")` 触发 `lastfm.c` 内的 curl HTTP 请求，无 fixture 注入点，库未暴露任何 mock/离线开关。

## test_package（消费者补全）

上游无可在隔离环境执行的断言套件，按守则「补全测试用例说明」勾「是」补全 test_package，离线验证库可链接且核心 API 符号可见：

- `test_package/test_clastfm.c` — 调用 `LASTFM_init("0","0")`（curl_global_init 不联网）+ `LASTFM_dinit()`，并静态检查 `LASTFM_STATUS_OK`/`LASTFM_PERIOD_COUNT`/`LASTFM_IMAGE_URL_OG` 等枚举符号可见。
- `test_package/CMakeLists.txt` — �接 `clastfm` + `curl`，构建 `test_clastfm`。
- `test_package/conanfile.py` — `test()` 跑 `test_clastfm`，输出 HMBS 证据标记。

不联网、不凭据，仅验证「库被 Conan 正确产出、头文件可 include、API 符号可链接调用」——这是消费者视角的最小实质断言（R34）。

## 验证结果

真机预检（HMBS 调度，环境与官方 CI 同源）：

- 编译：`./configure --enable-static --disable-shared && make -j1` 通过，产出 `libclastfm.a` + `clastfm.h`。
- `make check`：上游无 check target，`Making check in src: Nothing to be done for 'check'`。
- 上游测试套件：5 个集成测试均未运行（需在线凭据 + 外网），见上方审计。
- test_package：1 个断言（`LASTFM_init`+`LASTFM_dinit` 成功）执行并通过。

实跑命令与环境细节见本文件上方；HMBS 标记由真机测试命令结束后产生。

## 注意事项

1. **HMDFS 权限（L1 平台真理）**: autotools 项目的 configure/config.status 需将临时目录建在 `$TMPDIR`（不在 HMDFS 挂载点）并去掉 `umask 077`，否则进程无写权限（E011/E046）。
2. **curl 依赖（cmd-pkgs 预编译包，非 Conan dep）**: 制品仓 ohpcd remote 不分发 curl conan 包（两轮真机预检 `Unable to find 'curl/8.5.0'` 与 `curl/8.15.0@ohpcd/stable' in remotes`），conancenter remote 在 CI 被 disable（setup.sh `conan remote disable conancenter`）。解法：`generate()` 用 `cmd-pkgs install.sh` 装 curl 8.19.0 预编译包到 `$DEFAULT_PREFIX`，设 `PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig` + `-I$PREFIX/include` + `-L$PREFIX/lib` 喐给上游 `PKG_CHECK_MODULES(CURL,libcurl)`。cmd-pkgs curl 8.19.0 含 `curl/curl.h` + `libcurl.pc`（curlpp 0.8.1 / bibtexconv 2.2.2 已验证可用）。本轮踩坑：初版写 `self.requires("curl/8.15.0@ohpcd/stable")` → 预检 resolve 失败；二版裸 `curl/8.5.0` 仍 resolve 失败 → 第三轮改为 cmd-pkgs 装包。
3. **`AutotoolsToolchain.environment` 是方法不是对象（conan 2.30）**: 不能用 `tc.environment.define("KEY", val)`，会报 `AttributeError: 'function' object has no attribute 'define'`。正确范式是 `os.environ["KEY"] = val`（configure 子进程继承 os.environ）。
4. **config.guess 不认 HarmonyOS（E007）+ HMDFS tmp 探测失败**: 上游 2012-02-10 config.guess 既不认 `uname -s = HarmonyOS` 又在 HMDFS tmp 建 dummy.c 时权限拒绝。解法：`tc.configure_args.append("--build=aarch64-unknown-linux-gnu")` 显式 build triplet，configure 跳过 config.guess 完全不运行。参考 bash 5.3 / bmon 4.0 / berkeley-db 4.8.30 / dateutils 0.4.11。
5. **非命令行工具**: libclastfm 产物仅为库，无 `bin/`，不需要 `commands.json` (R38)。
