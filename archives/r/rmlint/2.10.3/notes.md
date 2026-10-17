# rmlint 2.10.3 适配笔记（HarmonyOS PC / aarch64）

- 构建系统: **SCons**（上游 `SConstruct` + `lib/SConscript` + `src/SConscript` + `tests|po|docs|gui/SConscript`）
- 编译器: clang 15.0.4（conan profile `tools.build:compiler_executables.c` = `/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- 依赖: `glib/2.84.0.1`（唯一必需）、`pkgconf/3.0.5`（tool_requires）
- 源码: `https://codeload.github.com/sahib/rmlint/tar.gz/refs/tags/v2.10.3`
  sha256 `8ffdbd5d09d15c8717ae55497e90d6fa46f085b45ac1056f2727076da180c33e`（2,504,233 字节，真机下载实测）
- 状态: 见 `manifest.yaml`（本地 create/W3 判决未落地前不得写 built）

## 1. 三个决定路线的问题 —— 实测读数

### 1.1 SCons 在设备上到底有没有
| 探针 | 结果 |
|---|---|
| `command -v scons` / `scons-3` / `ascons` | 全部无输出（不存在） |
| `python3 -c "import SCons"` | `ModuleNotFoundError: No module named 'SCons'` |
| `conan download scons/4.8.1 -r=ohpcd --only-recipe` | `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`（⇒ 制品仓无此配方；同命令对 glib 是成功的） |
| 上游是否自带 | 否，`SConstruct` 无 vendored SCons |

⇒ **不能 `tool_requires`**。仓内既有做法（均已合并进 main）：
`archives/g/gpsd/3.26`、`archives/d/dxx-rebirth/0.6`、`archives/v/vixl/5.1.0`
一律在 `generate()` 里
`python3 -m pip install --no-input --target=<build_folder>/_scons_env scons==<ver>`
+ 把 `PYTHONPATH` 存成 build 环境脚本 + 调 `python3 -m SCons`。
本配方沿用该形态（`_scons_version = "4.10.1"`，与 gpsd 同版）。

**边界说明（不是绕过门禁）**：安装目标是 **Conan 构建目录内的私有前缀**，
不写 `--user`、不写 site-packages、不动 `~/.local`，随 `conan create` 的沙箱一起生成与销毁，
与三份已合并配方同构。真机验证（隔离目录，未污染用户环境）：
`pip install --target=<tmp> scons==4.10.1` → `SCONS_IMPORT_OK 4.10.1`、
`python3 -m SCons --version` 正常打印 v4.10.1 banner。

`SCons.Platform.posix` 的 `SHELL='sh'` patch（gpsd/vixl 同做法）：OHOS 无 `/bin/sh`，
但存在 `/system/bin/sh`（实测 `-rwxr-xr-x root shell 306288`）。patch 写成
"目标串不存在即 noop"，因此上游版本变动不会炸构建。

### 1.2 硬外部依赖闭包（逐个精确实测，未用通配 conan list）
| 依赖 | 是否必需（源码依据） | 实测结论 |
|---|---|---|
| `glib-2.0 >= 2.64` | **必需**：`SConstruct:612 conf.check_pkg('glib-2.0 >= 2.64', 'HAVE_GLIB', required=True)` | ohpcd **配方+二进制均在**：`conan install --requires=glib/2.84.0.1 --build=never` → `Package installed b55f7a483155972128ae18c9f9e8c67eba35e745`（glib 为 **shared** 变体，产物含 `lib/libglib-2.0.so`） |
| `pkgconf` | 必需（构建期）：`pkg_config = os.getenv('PKG_CONFIG','pkg-config')`，全依赖经 pkg-config 发现 | `conan install --requires=pkgconf/3.0.5 --build=never` → `Install finished successfully`；仓内 54 处 `tool_requires("pkgconf/3.0.5")` 先例 |
| `libyaml` | **不使用**！2.10.3 全树 grep `yaml` 零命中（SConstruct/src/lib 均无），配置解析自研 `lib/cfg.c` | 不需要依赖（**与常见认知相反，值得记一笔**） |
| `uuid` | 不使用 | 不需要 |
| `blkid` | 可选：`check_pkg('blkid', required=False)` + `check_blkid()` | ohpcd **无配方**（`util-linux-libuuid/libuuid/util-macros` 精确探测均报 acceleration policy 错），全仓 archives 亦 0 处 `requires("*blkid*")` ⇒ **关闭** |
| `json-glib-1.0` | 可选：只用于"读 json 缓存" | 关闭（见 §3） |
| `libelf` | 可选：`<libelf.h>` 实测不在 OHOS sysroot | 关闭 |
| `xattr`（getxattr/setxattr/l*） | 由 libc 提供，无独立库 | **保留开启**：sysroot 有 `sys/xattr.h`、`linux/xattr.h`、`linux/fs.h`、`linux/fiemap.h`、`sys/ioctl.h`（用 profile 的 clang 逐个 `-fsyntax-only`+链接实测均 OK） |
| `-lm -lpthread -lrt -ldl -lutil` | SConstruct 追加 `-lm`，glib 需 `-lpthread` | 实测全部链接 OK（SDK sysroot 自带桩） |

⇒ **依赖闭包已全绿，无需 `$P block` 转手**（唯一未发布的 blkid/json-glib 是可选面，已按路径 A 关掉）。

### 1.3 pkg-config 接线（本包最容易踩空的机制）
- glib 包**自带** `.pc`，但 `prefix=/`（`glib-2.0.pc` 里 `prefix=/`、`libdir=/lib`）⇒ **不可直接用**。
- `PkgConfigDeps` 对**直接依赖**的 glib **会**重新生成正确 `.pc`：实测生成
  `glib-2.0.pc / gio-2.0.pc / gobject-2.0.pc / gmodule-2.0.pc / gthread-2.0.pc / glib-2.0-unofficial.pc`，
  其中 `prefix=/storage/Users/currentUser/tmp/ch/home-z24-rmlint/p/glibcad7259522c98/p`（绝对、正确）。
- **但不会生成 `gio-unix-2.0.pc`**（Conan glib 配方未声明该 component）⇒ `HAVE_GIO_UNIX=0`。
  影响面仅为"用 ioctl 判断非旋转盘"这一优化，且该优化同时需要 blkid（已关）⇒ 路径 A 无损。
- `.pc` 写在 `generators_folder`，而 conanbuild 环境**不会自动**把该目录塞进 `PKG_CONFIG_PATH`
  （CI 实测教训见 `archives/a/abiword-plugin-docbook/3.0.8/conanfile.py:162-166`）。
  本配方在 `generate()` 里 **先** `buildenv_info.append_path("PKG_CONFIG_PATH", generators_folder)`
  **再** `VirtualBuildEnv.generate()`（顺序错了注入不生效）。
- 另一关键点：`SConstruct` 建 Environment 时把子进程环境**裁剪**为
  `['PATH','TERM','HOME','PKG_CONFIG_PATH']`（`options['ENV']`）。
  ⇒ 只有这 4 个变量能传到真正的编译/链接命令；**因此 pkg-config 的发现只能靠 `PKG_CONFIG_PATH`，
  靠 `CFLAGS`/`LDFLAGS` 注入是无效的**；`CC/AR/RANLIB` 必须由 SCons 命令行变量给
  （SConstruct 从**外层** `os.environ` 读 CC/CFLAGS/LDFLAGS/AR/NM/RANLIB，也支持命令行 VAR=）。

### 1.4 文件系统能力面（B 潜力位 + 主要风险）
真机探针 `~/tmp/uc2/z24-rmlint/probe_fs.out` + `probe_hdr.out`（目录 = `$HOME/tmp/...`，即 HMDFS）：

| 能力 | 实测 | 依据/备注 |
|---|---|---|
| `link(2)` 硬链接 | **不支持** | `ln: cannot create hard link from 'f1' to 'f2': Operation not permitted`，`ls -li` 显示 nlink 恒为 1。`mount` 显示 `/storage/Users` 是 `tmpfs ... hmmac=use_task`（hmdfs 视图，根 fs 是 hmfs 但经 hmdfs 转发）；`/data/service`、`/tmp`、`/dev/shm` 均不可写，**没有可建硬链接的落点** |
| `symlink(2)` | 支持 | `SYMLINK_OK` |
| xattr `user.*` | **支持且可回读** | `setfattr -n user.test -v hello f1` → OK；`getfattr -n user.test --only-values` → `hello`；文件已有 `security.isolate` / `security.selinux="u:object_r:hmdfs:s0"` / `user.hmdfs.perm` |
| inode 唯一性 | 支持 | 两个不同 inode 号 |
| `fallocate` | **EACCES** | `fallocate failed: Permission denied`；`lseek`+write 伪稀疏可写但 `st_blocks=24`（4,194,305 字节文件仅占 12 KiB，非上游预期的稀疏语义） |
| `SEEK_DATA/SEEK_HOLE` | Python 侧无常量 | `AttributeError: module 'os' has no attribute 'SEEK_HOLE'`（`os.SEEK_DATA` 同样缺） |
| 目录遍历 | 支持 | `os.walk`/`os.listdir`/`os.fstatvfs` 正常（`f_files=48455677`） |
| 头文件 | 齐全 | `sys/xattr.h` `linux/xattr.h` `sys/ioctl.h` `linux/fs.h` `sys/vfs.h` `sys/statfs.h` `glob.h` `fnmatch.h` `endian.h` `execinfo.h` `ucontext.h` 全部可编译；`attr/xattr.h`、`sys/endian.h` 不存在（rmlint 不用 libattr 头，用 `sys/xattr.h`） |

对**构建**的影响：无（rmlint 编译不需要 link(2)）。
对**运行**的影响：只读/报告类功能（扫描、校验和、格式化输出）不受影响；
`reflink`/`unlinker`(硬链接)/`xattr` 写缓存/稀疏优化等**动作型**模式在 HMDFS 上受限。
对**上游测试**的影响：见 §4，是硬伤。

## 2. 构建配方要点（最终方案）

- `source()`：`get(self, **conan_data["sources"], strip_root=True)`；
  conandata 必须显式 `filename: rmlint-2.10.3.tar.gz`（URL 末段是 tag 名、无后缀 ⇒ conan 会误判 ZIP、`strip_root` 失败）。
  顶层目录 `rmlint-2.10.3/`，strip 成立（实测 `tar tzf | head`）。
- `generate()`：装 SCons → patch posix SHELL → `PkgConfigDeps` → 追加 `PKG_CONFIG_PATH=generators_folder` → `VirtualBuildEnv.generate()` → 存 `scons_env`（PYTHONPATH）。
- `build()`：`python3 -m SCons -j1 CC=<conf c> AR=<ar> RANLIB=<ranlib> <_disabled_features>`，`cwd=source_folder`。
  默认目标 = `librmlint`（`lib/SConscript env.Library('../rmlint', ...)`）+ 程序（`src/SConscript env.Program('../rmlint', ...)`，产物在源根 `./rmlint`）+ man page（`docs/SConscript env.Default(manpage)`）。
  man page 的 action 在找不到 sphinx 时**自行 return**（`run_sphinx_binary` 首行 `if sphinx_binary is None: return`），所以默认目标不会因缺 sphinx 失败。
- `package()`：**不走 `scons install`**。原因：`docs/SConscript` 把 `manpage` 也挂进 `install` alias
  （`env.Alias('install', [manpage, man_install])`），而 sphinx/rst2man 在本平台不存在（实测 `rst2man`/`rst2man.py` ABSENT），
  install 会去装一个不存在的产物。⇒ 直接 `copy 'rmlint' → bin/` + `COPYING`/`README.rst → licenses/`
  （与已合并的 `a/abr2gbr/1.0.2`、`v/vamps/0.99.2` 同做法；`lib/SConscript` 里 `INSTALL_LIBRARY = False`，
  上游本来也不装静态库和头文件，rmlint 是纯工具包）。
- `package_info()`：`bindirs=["bin"]`，`libs/includedirs/libdirs` 清空（application 包，避免下游误链 `librmlint.a`）。

## 3. 关掉的可选面（上游开关名，路径 A）

| 开关（上游 `AddOption`，`SConstruct:509-516`） | 状态 | 原因 |
|---|---|---|
| `--without-blkid` | 关 | 依赖 `blkid` pkg-config 模块与 `<blkid.h>`；ohpcd 无配方、archives 全仓 0 处引用。影响：失去"非旋转盘识别"优化（`HAVE_BLKID`） |
| `--without-json-glib` | 关 | `json-glib-1.0` 只用于**读取** json 缓存（`HAVE_JSON_GLIB`）；写 `-o json` 用内建 formatter，不依赖它。ohpcd 无配方 |
| `--without-libelf` | 关 | `<libelf.h>` 不在 OHOS sysroot。影响：`rmlint -T ns`（未 strip 二进制）Finder 类型不可用 |
| `--without-gettext` | 关 | `po/SConscript` 需要 `msgfmt`；设备上的 `msgfmt` 位于 `~/.harmonybrew/bin`（用户级、CI 干净环境不可见）⇒ 按 W0b「历史命令在 CI 逐字可执行吗」判为不可依赖。影响：无本地化 |
| `--without-gui` | 关 | `gui/SConscript` 装 python GTK 前端（`rmlint.py` GUI），非本次交付面 |
| `--without-compile-glib-schemas` | 关 | 无 gsettings/dconf schema 需编译（GUI 已关） |
| fiemap（`--with-fiemap`，保持默认开） | 开 | `linux/fiemap.h` 实测存在，探测失败也只会把 `HAVE_FIEMAP=0`，不阻塞 |
| xattr / lxattr | 开 | `getxattr/setxattr/l*` 由 libc 提供、`sys/xattr.h` 存在，且 HMDFS 实测支持 `user.*` 读写 |
| bigfiles | 自动 | `off_t` 在 aarch64 为 8 字节 ⇒ `HAVE_BIG_OFF_T` 预期成立（未单独实测运行期 >4GiB 文件） |

## 4. 上游测试（rule4 口径）

**上游注册总数（os.walk 实测，未用 shell 通配）**：
`tests/` 66 个文件，其中 `test_*.py` **44 个**，注册 `def test_` 函数 **149 个**。
执行器：`tests/SConscript` 的 `test` alias → `pytest -s -v -k "not slow"`；
`tests/requirements.txt` 钉 `pytest==8.*`、`psutil==7.*`、`xattr==1.*`。

**实测通过 / 跳过 / 失败：0 / 149 / 0 —— 本轮未执行**（不写"通过"，见 `test_package/MANIFEST.yml`）。
逐条技术原因（分类码 + 受影响文件清单在 MANIFEST.yml 中 44 条逐条列出）：
- `R2`（runner 缺失，**44 文件全部命中**）：`command -v pytest` → ABSENT；`python3 -c "import pytest"` → `ModuleNotFoundError`。psutil 需 C 扩展编译、xattr 需 cffi，均非本平台既有件。
- `R1`（硬链接夹具不可建，绝大多数用例命中）：`tests/utils.py:326-327`
  `def create_link(path, target, symlink=False): f = os.symlink if symlink else os.link`
  ⇒ 硬链接是该测试框架的**公共夹具**，而 HMDFS `link(2)` 实测 EPERM（§1.4）。
- `R3`（reflink/稀疏/fallocate）：`test_mains/test_is_reflink.py`(13)、`test_mains/test_dedupe.py`(6)、`test_robustness/test_bigfiles.py`(2)；`fallocate` 实测 EACCES、`os.SEEK_HOLE` 常量缺失。
- 其他：`test_types/test_nonstripped.py`(3) 还额外依赖本轮关掉的 libelf。

**本轮未尝试执行的原因（如实）**：两台共享构建主机的构建槽整场为满
（`build-slot.sh --status` → `SLOT_STATUS: 本机长杆 2/2 · 机动 1/1（硬上限 3）→ 全满，等释放`），
按规则不硬起、不 kill 他窗进程。跑 pytest 需要先有产出的二进制。

**test_package 新增 6 个消费者用例**（`test_package/test.sh`，全部避开硬链接/xattr 写/fallocate/reflink）：
`--version`、`--help`、真实重复检出（点名两个孪生路径 + duplicate 汇总 + rc=1）、
`-o json -O` 机器可读报告（含两路径 + size/checksum）、**负向对照**（互异目录必须 rc=0 且不报 duplicate）、
`-T ed` 空目录类型。`conanfile.py::test()` 复核 `test.sh` 写出的 summary 文本标记，缺一个即 `ConanException`。

## 5. 已试过的失败方案（勿重复）

1. **空 CONAN_HOME 判依赖** —— `~/tmp/ch/home-z24-rmlint` 目录已存在但没有 `ohpcd` remote
   （只有默认 `conancenter`）⇒ 首轮 6 个依赖**全部误报 RECIPE_MISSING**，包括明明已发布的 glib。
   修复：从 `home-z24-quagga` 拷 `remotes.json`，并在 `global.conf` 写
   `core.sources:download_cache=/storage/Users/currentUser/tmp/ch/dlcache`；
   复测 `conan remote list` 出现 `ohpcd ... Enabled: True` 后 glib/libyaml/zlib 全 `RECIPE_OK`。
   （⇒ 这正是规则里"空 home 把已发布依赖误报成未发布 ⇒ 可能错手 `$P block`"的实拍复现。）
2. **裸 `cc` 探头文件** —— `cc: inaccessible or not found`，且 `find / -noqueryfs -path "*/include/sys/xattr.h"` 报 NOTFOUND，
   两条合起来会把"sysroot 根本没有 xattr.h"写成结论。实际用 profile 的
   `/data/service/hnp/bin/clang` 重测，`sys/xattr.h`/`linux/fs.h`/`sys/ioctl.h` **全部可编译**。
   ⇒ 头文件探针必须用 profile 注入的编译器绝对路径，`find /` 在本平台不可信（挂载视图被裁剪）。
3. **`curl -sIL` 判 GitHub 可达性** —— 两种 URL 均返回 `000`，看起来"官方源不可达、必须上镜像"；
   同脚本改用 `curl -sL`（GET）后 codeload 成功落地 2,504,233 字节。
   ⇒ 本包判可达性**必须用 GET**。也印证 `ghfast.top` 不需要、不该塞（R39/PF7 镜像黑名单）。
4. **用 glib 自带的 `.pc`** —— `prefix=/` 指向根目录，pkg-config 会解析到不存在的 `/include/glib-2.0`。
   ⇒ 必须走 `PkgConfigDeps` 生成的那份。
5. **`conan config get core.sources:download_cache`** —— 本机 conan 2.29.1 无 `get` 子命令
   （只有 clean/home/install/install-pkg/list/show）⇒ 该写法直接 rc=2。

## 6. 适用边界与后续风险

- 本配方是 **application 单文件产物**：只交付 `bin/rmlint`。若日后要 GUI（`--with-gui`）或 json 缓存回放（`--with-json-glib`），
  得先把 `json-glib`/`blkid` 作为**依赖项任务**立项发布，不能在本 PR 捎带（PF1/R36）。
- `rmlint` 的**动作型模式**（`--reflink`、`--unlinker` 去重、把校验和写进 xattr）在 HMDFS 上会因
  `link(2)` EPERM / `fallocate` EACCES 失败或退化；**只读扫描与报告**不受影响。
  若审查要求给"能力面"结论：本包按路径 A 交付**扫描-报告**能力，不承诺**改写-去重**能力。
- 上游 `check_sys_block()` 用 `os.access('/sys/block', R_OK)`，本平台未实测该路径；失败也只会置 `HAVE_SYSBLOCK=0`。
- SCons 由 pip 在构建沙箱内自举 ⇒ **构建期需要 PyPI 社区源可达**。gpsd/dxx-rebirth/vixl 三个已合并配方同形态，
  CI 侧已被证明可行；若某轮 CI 的 pip 源抖动，症状会是 `generate()` 阶段失败，不是链接期失败。


## 7. 续跑增补（2026-09-25，z31-rmlint 子代理）——五个新实测事实 + W3 全绿判决

> 本节修正/细化前文两处早期判断：§1.3 末段「HAVE_GIO_UNIX=0 ⇒ 路径 A 无损」被证伪；
> §4 的「本轮未尝试执行」在本轮已实际尝试并拿到更硬的收集期证据。均以本轮实测为准。

### 7.1 HAVE_GIO_UNIX=0 根本无法编译（修正 §1.3）
`lib/utilities.c` 只给 `#include <gio/gunixmounts.h>` 加了 `#if HAVE_GIO_UNIX` 守卫（第 56 行），
而 `rm_util_same_device()`（约 1137 行）对 `g_unix_mounts_get()` 的调用**无守卫** ⇒
HAVE_GIO_UNIX=0 时 GUnixMountEntry/g_unix_mounts_get 未声明，clang 直接报错（G2 实测）。
头文件与符号实测都在已发布 glib 包里 ⇒ 修复 = 在 `generate()` 里从 `gio-2.0.pc` 派生
`gio-unix-2.0.pc`（仅改 Name/Description 两行），让 HAVE_GIO_UNIX=1，零上游改动。

### 7.2 真机首崩：getpwuid NULL 解引用（已修，patches/0001）
G2 编译通过后，test_package 用例 3 扫描即崩，且 SIGSEGV 处理器循环打印
（dup.out 曾达 3.1GB；SA_RESETHAND 预期的「处理一次即默认终止」在 OHOS 内核上未发生，
处理器返回后同一故障指令反复重交付——实测现象，机制未深究）。
定位链（gdb 在 OHOS 被 ptrace 禁用，改用 fprintf 打点二分，SCons 增量重编 <1min/轮）：
`main → rm_cmd_main → rm_fmt_set_state(INIT) → pretty formatter`
→ `rm_fmt_head → rm_util_get_groupname()`：
`getpwuid(geteuid())` 返回 NULL（**HarmonyOS 应用 uid 在 passwd DB 无条目**），
代码直接取 `user->pw_gid` —— 同文件 `rm_util_get_username()` 有检查，此处漏了。
修复 = `patches/0001-lib-utilities-null-check-getpwuid.patch`（纯 POSIX NULL 检查，
无平台宏，patch_type=portability）；修后同一扫描 0.054s 完成（调试副本实测）。

### 7.3 baduid finder 污染 + 退出码语义（修正 §4 假设）
- 崩溃修掉后默认类型集下两个相同文件报 **Bad UID(s): chown (null)**、
  "0 are duplicates"——OHOS 无 passwd 条目 ⇒ 每个文件都先进 baduid finder，
  重复检测永远轮空。**本平台重复检测必须 `-T df`**（test_package 用例 3/4/5 已用并注释）。
- **rmlint 2.x 成功扫描恒返回 0**（`lib/cmdline.c rm_cmd_main` 仅内部 BUG/中断/
  --equal 模式返回非 0）——原 test.sh 的「rc==1 即发现重复」是未验证假设，
  已改为断言报告文本（孪生路径 + "0 are duplicates in 0 groups" 精确零组行）。
- 另一实测：`-o/-O` 的格式化器**输出路径**含非 ASCII 字节时（本 worktree 名含中文），
  GOption 的字符串转换在 C locale 下直接中止（glib "Invalid byte sequence in
  conversion input"，退出 1；`G_FILENAME_ENCODING=UTF-8` 救不了）；payload/扫描路径
  含中文则无碍。test.sh 用例 4 的报告因此写到 ASCII 的 `$HOME/tmp` 并自清理。

### 7.4 上游 pytest 套件：从「没跑过」到「收集期实测阻断」（细化 §4）
本轮真机实测（证据均在 ~/tmp/uc2/z31-rmlint/）：
- pytest 8.4.2 可从社区 PyPI 源装上（纯 Python，隔离 target）——推翻「pytest 缺失」表述；
- 真正阻断 = `tests/utils.py:12` 模块级 `import psutil`：pytest --collect-only 实测
  即 ModuleNotFoundError（收集期 0 用例可达）；
- psutil 7.2.2：社区源完全无分发物；官方 PyPI sdist 自编在
  `linux/socket.h:23 redefinition of 'sockaddr_storage'`（OHOS sysroot 与 musl 定义冲突，
  psutil/arch/linux/net.c）失败 —— psutil 在本平台**当前不可构建**；
- 五维账本维持 **149 注册 / 0 可执行 / 0 通过 / 0 跳过 / 0 失败**，但「0 可执行」从推断
  升级为实测收集期失败；逐条技术原因 R1-R4 不变。

### 7.5 两个流程坑（续跑 11 轮才全绿，均为实测）
- **conan create 缓存命中会整体跳过构建**：改了配方/补丁但本地缓存里还有同 package_id
  的旧二进制时，`--build=missing` 直接复用旧包（曾连续两轮拿旧二进制跑测试）。
  ⇒ 改配方后必须 `conan remove "rmlint/*" -c` 再 verify。
- **ohc-run 的 E017 镜像注入回滚会还原 conandata.yml 旧快照**：上一轮异常退出留下的
  `conandata.yml.ghfast-bak` 在下一轮启动时被当「崩溃残留」恢复，期间对 conandata.yml 的
  新增（patches 段）被整体吃掉 ⇒ 补丁没打上还看不到原因。⇒ 异常退出后开工先
  `rm conandata.yml.ghfast-bak` 并核对 conandata.yml 完整性。

### 7.6 W3 终判（原样摘录）
```
ℹ️ G2: conan create (干净构建)...
✅   G2: PASS
ℹ️ G3: 系统同名库隔离验证 (R26)...
✅   G3: PASS
ℹ️ G4: 产物完整性检查...
ℹ️ L2: 平台功能矩阵 (smoke test)...
ℹ️ L4: 静态安全扫描 (checksec)...
ℹ️ L5: 产物基线对比...
✅
✅ 配方验证通过: rmlint 2.10.3
✅    可标记 status: published
```
test_package 六用例 6/6 PASS（summary 原文：version_flag / help_flag / duplicate_detected /
json_formatter_output / clean_tree_reports_nothing / empty_dir_type 全 PASS）。
W4 审计：`reports/audit-result.json` verdict=pass，P0=0 P1=0 P2=3（文档措辞类，不阻断）。

---

**最终状态**: built
