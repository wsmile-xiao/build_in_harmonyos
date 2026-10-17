# libprintsys 0.6 适配笔记

## 上游身份

- 名称/版本：libprintsys 0.6（`AM_INIT_AUTOMAKE(libprintsys,0.6)` 实证）
- 描述：printcap parser, helper for gnulpr's printfilters
- 主页：https://lpr.sourceforge.net/ （GNU gnulpr / LPR-ng 项目，作者 valinux.com 时代，2000-2001）
- 不是 OpenHarmony 组件：官方 manifest `ohos/ohos.xml` 中 print 子系统只有
  `print_print_fwk`（组件名 print_fwk）与 `applications_print_spooler`。

## 源码来源（R39/PF7 例外，需在 PR 说明）

上游已停更且发布物不可获取，实测：

```
https://downloads.sourceforge.net/project/lpr/libprintsys/0.6/libprintsys-0.6.tar.gz  404
https://downloads.sourceforge.net/project/lpr/libprintsys/libprintsys-0.6.tar.gz      404
https://sourceforge.net/projects/lpr/files/libprintsys/latest/download                404
https://deb.debian.org/debian/pool/main/l/libprintsys/                                404
https://sourceforge.net/api/file/index/project-id/3800/...                            404 (旧 API 已下线)
```

采用该源码包 `debian/control` 中 **Vcs-Git 自行声明的官方仓库**
`https://salsa.debian.org/debian/libprintsys` 的 GitLab archive 端点：

```
url    https://salsa.debian.org/debian/libprintsys/-/archive/master/libprintsys-master.tar.gz
sha256 59192bb22c41f0a954a085ac723ad781220e1d43ca21ddf2dee9762e7b2aba0a
```

该仓库为 3.0 (quilt) 的 **unpatched 布局**：`debian/patches/debian.patch` 未施加于工作树
（工作树里 `configure.in` 仍是 `AM_PATH_GLIB(1.2.0)`），因此本配方不依赖 Debian 的补丁。

## 依赖（W0 实测，全部可消费）

| 依赖 | 版本 | 类型 | 依据 |
|---|---|---|---|
| glib | 2.88.3 | 强制（编译+链接） | `#include <glib.h>`，24 个 `g_*` 未定义符号；`AM_PATH_GLIB(1.2.0)` |
| tdb | 1.4.15 | 强制（编译+链接） | `#include <tdb.h>` + `tdb_open/fetch/store/close`；`AC_CHECK_LIB(tdb,tdb_store)` |
| libffi/pcre2/proxy-libintl/zlib | glib 传递 | 间接 | `conan install` 依赖图实证 |
| pkgconf | 3.0.6 | tool_requires | shim 经 pkg-config 解析 flags |

注：`conan download tdb/1.4.8|1.4.12|1.4.13|1.4.14|2.4.1|2.8.0` 均为 rc=1，
**制品仓实际发布的是上游版本 1.4.15**（勿按 Debian 版本线取号）。

## 关键适配点（4 处，均有实证）

### 1. glib-config 探测（补丁 0001/0002 + 配方内 shim）
`configure.in` 用 `AM_PATH_GLIB(1.2.0)`，包内 `configure` 由 **autoconf 2.13** 生成，
只探测 `glib-config`（GLib 1.x 专有，现代系统不存在）。

配方在 `generate()` 里生成一个 `glib-config` shim（flags 由 PkgConfigDeps 的 .pc 解析，
并折叠 tdb），用 `GLIB_CONFIG=` 环境变量喂给原样运行的 configure —— 因此**不需要
automake/libtool 重生成**（本机与 CI 均无 automake）。

平台三元组问题按知识图谱条目处理：
- **E007** `patch-autotools-ohos.pl` → config.guess 输出 `aarch64-unknown-linux-ohos`
- **E122** config.sub 的 kernel-os 验证列表补 `linux-ohos*-`
  （E122 给的 sed 锚点 `linux-uclibc*- )` 与本版本结构不符，实际锚点是 `linux-mlibc*- )` 行）
- 明确**不使用 `--host/--build`**（E007 禁止：会让 AC_RUN_IFELSE 全部跳过）

### 2. ltconfig 不认 OHOS（补丁 0003）
包内 `ltconfig` 是 **libtool 1.3.3（1999-07-02）**。它的
"Transform linux* to *-*-linux-gnu*" case 写在 `host_os` **赋值之前**，规范化永不生效，
于是 `host_os` 保持 `linux-ohos`，匹配不到任何 OS 分支 → `dynamic_linker` 未设置 →
`can_build_shared=no` → **只产出 libprintsys.a，没有 .so**。

修法与同仓先例 `archives/c/cpu/1.4.3/patches/0003-configure.patch` 同构：把
`linux-ohos*` 并入 `linux-gnu*)` 分支。修后 `checking dynamic linker characteristics... Linux ld.so`。

### 3. tdb flags 被 Makefile.am 收窄
`src/Makefile.am` 把两侧都限定为 glib：`INCLUDES=$(GLIB_CFLAGS)`、`LDFLAGS=$(GLIB_LIBS)`。
因此从外部传 LDFLAGS 里的 `-L<tdb>` 会被**静默丢弃**，链接报
`ld.lld: error: unable to find library -ltdb`。解法：shim 的 `--cflags/--libs` 同时输出
`glib-2.0` 与 `tdb`，让 tdb 借这两个变量进入编译与链接。

### 4. libprintsys.so 缺 DT_NEEDED（配方内 relink，最重要）
`ltconfig` 的 `archive_cmds='$CC -shared $libobjs $deplibs $linkopts …'` 会把
conan 路径下的 `-lglib-2.0/-ltdb` 归入 `old_deplibs` 而非 `$deplibs`，**根本不交给 linker**
（对照证据：同一 libtool 链接的 `pcap` 可执行 NEEDED 完整）。结果 .so 只有 libc.so，
却带 24 个 `g_*` + 4 个 `tdb_*` 未定义符号，消费者必然失败：
- 链接期：`ld.lld: error: undefined reference due to --no-allow-shlib-undefined`
- 运行期：`Error relocating libprintsys.so.1: g_list_prepend: symbol not found`

已验证**无效**的路线（不要再试）：shim 里加 `-Wl,--no-as-needed`（能进 GLIB_LIBS/LDFLAGS/LIBS，
但 .so NEEDED 不变）、给 `src/Makefile.in` 补 `libprintsys_la_LIBADD=$(GLIB_LIBS)`
（.libs/*.o 在 package 阶段已不存在，且仍不写 NEEDED）、
`cpp_info.sharedlinkflags/exelinkflags` 传 `--allow-shlib-undefined/--no-as-needed`
（CMakeDeps 不传导，运行时仍失败）。

采用方案：`package()` 里用已安装的 `libprintsys.a` + `-Wl,--whole-archive` +
`-Wl,--no-as-needed` 直接重建 .so（修复产物本身，不把负担推给消费者），
重建后 NEEDED 含 `libglib-2.0.so.0`、`libtdb.so.1`。HMDFS 不能覆盖软链接，
故先 `os.remove` 再 `os.symlink`（R9）。

## 其他

- **`lps_end()` 内部已调用 `printcap_end()`**（printsys.c:91），因此调用方**不应**再显式
  调 `printcap_end()`：`printcap_end` 会 destroy 并把 `name_lookup` 置 NULL，随后 `lps_end`
  二次 destroy 触发 `GLib-CRITICAL: g_hash_table_destroy: assertion 'hash_table != NULL' failed`。
  上游自带的 `pcaptest` 正是只调 `lps_init`/`printcap_write`/`lps_end`，本包 test.c 遵循同一契约。
- `printcap.h` 是公开 API（pcaptest.c 就 include 它）但 `Makefile.am` 只装 `printsys.h`
  → 配方 `package()` 显式补装。
- 删除打包产物里的 `.la`：其 dependency_libs 指向构建机的 glib/tdb 路径
  （Debian 为此在 0.6-6.1 被迫扩大运行时依赖），conan 自行解析依赖。
- 产物含可执行 `bin/pcap` → 按 **R38** 已建软件级 `commands.json`。

## 上游测试清点（R51）

`make -n check` 实测：

```
Making check in src
make[1]: Nothing to be done for 'check'.
```
`check-am: all-am`（Makefile:296 / src/Makefile:319）—— 上游 **无自动化测试**；
无 tests/ 目录、无 CMakeLists/CTest；唯一测试性产物是 `noinst_PROGRAMS=pcaptest`
（被编译不被运行，只调 lps_init/printcap_write/lps_end 且无断言；本机实测 rc=0）。

本包改由 test_package 从消费者视角做 **10 项行为断言**，实测 10/10 通过：
`libprintsys test: all checks passed (2 printers parsed)`

写测试样例时踩到的坑（记录以免重复）：printcap 条目**最后一行不能以 `\` 结尾**，
否则解析器会把下一条粘到当前条目上（表现为只解析出 1 个打印机 +
`g_hash_table_destroy: assertion 'hash_table != NULL' failed`）。这是测试样例的错误，
不是库的缺陷。

## PF5 / R8 例外说明

`0001-config.guess.patch` 新增 1 行 `+#elif defined(__OHOS__)`。它位于 config.guess 内部
**传给 C 预处理器做 libc 探测的 here-doc**（驱动 `GUESS=…-unknown-linux-ohos`，有实质逻辑，
非空壳守卫），属 R8 明文推荐的"通过修改 config.guess/config.sub 修复"手段，
也是 PF5 声明的例外场景。同仓 `origin/main` 上存在**同型新增行的 config.guess 补丁共 226 个**（任意 .patch 口径 256 个）
（`git grep` 统计，含 advancescan/aide/aj/ale/agensgraph/aiksaurus 等），均已通过 CI 合并。
若 PF5 仍拦截，按规则以 `--no-preflight` 留痕并在本 PR 说明上述依据。

### PF9 depth<5 例外（同批留痕）

`run_preflight` 另命中 1 条 PF9：`archives/l/libprintsys/README.md` 与
`archives/l/libprintsys/commands.json` 路径深度为 4 段（软件级文件本就落在
`archives/<字母>/<包名>/` 下）。这与 R38/§17「含可执行产物的包必须在**软件级**目录声明
commands.json」直接互斥 —— 满足 PF9 就无法满足 R38。
`origin/main` 上 depth-4 的 commands.json 有 2427 个、同时具备软件级 README.md 与
commands.json 的包有 1537 个（qbe/ko 等均已 CI 合并）；且 `run_preflight` 只被本地
`scripts/gitcode_pr.py` 的 create-pr 调用，CI 侧 `setup.sh`/`build_and_test.sh`/`junk_check.sh`
均不调用它（`build_and_test.sh` 反而硬性要求软件级 commands.json）。
故该命中不影响 CI 结论，与 PF5 一并以 `--no-preflight` 留痕。

## 验证结论（区分两套门禁，不混写）

`conan-verify`（配方自身门禁）：G0/G1/**G2 conan create**/G3 为 PASS；
其 G4 标题虽为 PASS 但正文是「无法找到程序包 ID」，L2/L4/L5 正文均为「跳过（无 cache 路径）」
——即这三项**未实测**，不可当作通过依据（真正的功能验证是 test_package 的 10 条断言与
W3 的 L1/L5，链接正确性另以 `llvm-readelf` 复核）。

`finish` 的 W3 本地 CI 模拟（`build_and_test.sh`，与 CI 同源）实测逐条结果：

```
L1_RESULT=pass: test_package executed
L2_RESULT=skip: pcap version/help failed
L4_RESULT=warn: dangerous functions in patches
L5_RESULT=pass: bin/ has content
```

- `L2 skip` 属预期：`pcap` 是 printcap 解析器，上游未实现 `--version/--help`，
  smoke 探针无从判定，**不代表功能缺失**（功能由 L1 的 test_package 10/10 覆盖）。
- `L4 warn` 来自补丁内容：`0001/0002` 是整份 GNU config 脚本替换、`0003` 是 ltconfig
  shell 脚本，告警针对其中出现的 `strcpy`/`getenv` 等字符串，非本包新增 C 代码。
- W3 整体判定为通过（RC=0），故本包 status 如实保持 `built`；待 HEAD 的远程 CI 复算转绿并完成制品上传后方可标 published。

已知遗留（非本包引入，full 模式扫描可见）：`archives/c/cloog/0.21.1/.build-closed`、
`archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`
是存量误提交的运行时标记，会被 JC1/JC5 拦；本包按 incremental 模式（`git diff
origin/main...HEAD`）提交，故不受影响。这些标记现已在 `.gitignore` 中。
## CI 回归与修复（构建 #51352 → 转绿于 #51993）

事实：`AM_PATH_GLIB` 会**编译并运行** conftest。CI 上探测程序链接成功却加载不到
`libglib-2.0.so.0`，即 **build-scope 注入的 `LD_LIBRARY_PATH` 没有到达该 conftest**。
改为把 RUNPATH 直接写进探测程序（shim 的 `--libs` 为每个 `-L` 追加 `-Wl,-rpath`）后
CI 转绿（#51993：L0 结构、L1 测试执行、test_package 全通过），因为 DT_RUNPATH
随二进制携带，不经环境传导。

> ⚠️ 更正记录：本节初稿把根因写成「`self.dependencies.host` 只暴露直接 requires，
> 漏掉 pcre2/libffi/proxy-libintl/zlib 传递目录」。该说法已被第 4 轮 W4 审计实测证伪：
> `PkgConfigDeps` 生成的 `glib-2.0.pc`/`tdb.pc` **不含任何 `Requires`**，
> 因此 rpath 集合与原先 `LD_LIBRARY_PATH` 集合**完全相同**（都只有 glib、tdb），
> 传递闭包一个也没补上。真正起作用的仅是「用 DT_RUNPATH 绕开环境传导失效」。
> 保留此更正，以免后人按错误归因去改依赖遍历。

第二个坑（同轮审计抓出的本轮回归）：上游 `src/Makefile.am` 写 `LDFLAGS=$(GLIB_LIBS)`，
故 shim 新增的 `-Wl,-rpath` 会顺该变量**烘进 `bin/pcap` 的 RUNPATH**（构建机绝对路径），
初稿注释「never leaks into the product」不成立。修法：`build()` 在 configure 之后、
make 之前调用 `_strip_probe_rpaths()` 从生成的 `Makefile`/`src/Makefile` 剥掉
`-Wl,-rpath,*`。实测 `bin/pcap` RUNPATH 回到基线 `//lib`（RUNPATH 内 `.conan2` 命中 0），
NEEDED 仍为 libglib-2.0.so.0 + libtdb.so.1 + libprintsys.so.1。

因果验证（从零 conan create）：

| rpath | LD_LIBRARY_PATH | 结果 |
|---|---|---|
| 否 | 是 | 本机 PASS / **CI FAIL**（传导未到 conftest） |
| 是 | 否 | PASS |
| 否 | 否 | FAIL，逐字复现 CI 三行 |
| 是（make 前剥离） | 任意 | PASS 且 pcap RUNPATH 干净 ← 当前方案 |

教训：①configure 会**运行** conftest 的老 autotools 包，别指望 `LD_LIBRARY_PATH`
一定生效，给探测程序写 RUNPATH 更可靠；②上游把依赖变量塞进 `LDFLAGS` 时，
注入探测专用 flag 必须先确认它不会顺路进入产物；③「本机通过」不等于机制正确——
本机那份 glib 恰好 NEEDED 只有 libc.so，掩盖了传导失效。
---

**编译结束**: 2026-09-21 23:12
**最终状态**: built
