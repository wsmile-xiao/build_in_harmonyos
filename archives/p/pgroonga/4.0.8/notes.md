# pgroonga 4.0.8 — HarmonyOS PC 适配笔记

## 1. 概览

| 项 | 值 |
|----|----|
| 上游 | https://pgroonga.github.io/ （仓库 pgroonga/pgroonga） |
| 版本 | 4.0.8（GitHub Release tarball） |
| 源码 | `https://github.com/pgroonga/pgroonga/releases/download/4.0.8/pgroonga-4.0.8.tar.gz` |
| SHA256 | `09509b7c23f29bcb00d8c769b222156a023ee7ddd896ee875b0a4acdcd657498` |
| 构建 | Meson（`meson.build` 654 行；`project()` 未声明 `meson_version` 下限） |
| 包类型 | library（实际是 7 个 PostgreSQL `shared_module` + 扩展脚本） |
| 编译依赖 | `groonga/16.0.8`、`msgpack/7.0.1`、`libxxhash/0.8.3` |
| 构建期工具 | `tool_requires("postgresql/18.3")` |
| 产物 | `lib/{pgroonga,pgroonga_check,pgroonga_database,pgroonga_crash_safer,pgroonga_standby_maintainer,pgroonga_wal_applier,pgroonga_wal_resource_manager}.so` + `share/extension/{pgroonga,pgroonga_database}.{control,--4.0.8.sql}` |
| 补丁 | 无 |

PGroonga 把 Groonga 的全文检索能力做成 PostgreSQL 的 **index access method**：
`CREATE INDEX ... USING pgroonga (col)` 之后即可用 `&@`（全文）、`&@~`（查询
语法）、`&^`（词项前缀）、`&~`（正则）等运算符，以及 `pgroonga_*` 系列打分 /
高亮 / 分词函数。它同时给出 `pgroonga_database`（数据库级管理函数）与
`pgroonga_wal_applier` / `pgroonga_standby_maintainer` /
`pgroonga_crash_safer` 这几个 WAL 相关模块，专门解决 Groonga 自身存储与
PostgreSQL WAL 之间的一致性——这也是"为什么必须真起集群验证"的原因：这些
能力全部发生在服务端进程内部。

## 2. 五个适配要点

### 2.1 PostgreSQL 走 `tool_requires` 而非在 `build()` 里自举

同仓库的 `postgresql-topn/2.7.0` 是在 `build()` 里从源码自举一份 PG 树
（要额外处理 `config/install-sh`、`clang -E` 当 cpp 用等）。pgroonga 不需要：
CI 的 `-pr:b` 与 `-pr:h` 是**同一个 OHOS profile**，所以

```python
def build_requirements(self):
    self.tool_requires("postgresql/18.3")
```

直接解析到 ohpcd 已发布的 OHOS 制品，一次下载就拿到

```
include/postgresql/server/            服务端头（pgroonga 编译必需）
lib/postgresql/                        pkglibdir（含 pgxs/ 全套）
lib/postgresql/pgxs/src/test/regress/pg_regress   上游回归驱动（见 3.2）
bin/{initdb,pg_ctl,postgres,psql,pg_config}
share/postgresql/extension/{plpgsql.control,plpgsql--1.0.sql}
```

`pg_regress` 落在 `lib/postgresql/pgxs/src/test/regress/` 而不是 `bin/`，这不是
巧合：PostgreSQL 源码里 `src/test/regress/GNUmakefile` 的
`install: $(INSTALL_PROGRAM) pg_regress$(X) '$(DESTDIR)$(pgxsdir)/$(subdir)/'`，
而 `src/Makefile` 的 `SUBDIRS` 含 `test/regress`、`src/test/Makefile` 又把
`install` 递归进 `regress`——所以**完整 `make install` 一定带上它**。同仓库
`postgresql-sequential-uuids` / `postgresql-pllua` 之所以要自己下载 PG 源码树，
是因为它们需要一份**前缀非空**的 PGXS 树来构建扩展，而不是因为 `pg_regress`
缺失。

### 2.2 `pg_config` shim：Conan 的 PG 前缀为空

上游 `meson.build` 用 `pg_config` 反查安装位置：

| 查询 | Conan 包上返回（坏） |
|------|---------------------|
| `--includedir-server` | `//include/postgresql/server` |
| `--pkglibdir` | `//lib/postgresql` |
| `--sharedir` | `//share/postgresql` |
| `--bindir` | `//bin` |
| `--cppflags` | `-I//include/postgresql/server -I//include` |

`//` 在 Linux 上等价于 `/`，指向的是**文件系统根**而不是包目录。原因：Conan 打
的 postgresql 用 DESTDIR 安装、configure 前缀留空。

`generate()` 因此在 `<generators>/pgsql-bin/pg_config` 写一个只重定向
「路径类」查询的 shim，并用 `-Dpg_config=<shim>` 交给 meson；未知参数
（`--version` / `--configure` 等）原样 `exec` 真 `pg_config`。

```sh
case "$1" in
  --includedir-server) echo "<pkg>/include/postgresql/server" ;;
  --pkglibdir)         echo "<pkg>/lib/postgresql" ;;
  ...
  *)                   exec "$REAL" "$@" ;;
esac
```

> 这个坑对**所有**用 `pg_config` 反查安装位置的上游构建都成立（PGXS、
> autotools 的 `PG_CONFIG`、meson 的 `-Dpg_config=`），不是 pgroonga 特有。

### 2.3 groonga 的 `.pc` 烘焙了构建机前缀

`groonga/16.0.8` 包内的 `groonga.pc` 前缀指向构建机路径，`dependency('groonga')`
会把 `-I/-L` 指到不存在的目录。配方用

```python
generators = "PkgConfigDeps"
```

让 Conan 按当前包目录**重新生成** `groonga.pc`（以及 `msgpack-c.pc` /
`libxxhash.pc`）；`MesonToolchain` 会自动把 generators 目录写进
`pkg_config_path`，所以 meson 的 `dependency('groonga', version: '>= 14.1.0')`
命中的是新生成的那份。

### 2.4 `install_to_postgresql=false` + `datadir=share`

上游默认 `install_to_postgresql=true` 会把模块装到 `pg_config --pkglibdir`。
Conan 里那个路径不属于本包（也不可重定位），因此：

```python
tc.project_options["install_to_postgresql"] = False
tc.project_options["datadir"] = "share"
```

第一条让模块落 `get_option('libdir')`（包内 `lib/`）。第二条要特别说明：
`MesonToolchain` 会把 `datadir` 直接设成 `resdirs[0]`（也就是 `"res"`），
于是扩展脚本落到 `share/res/extension` —— 目录结构看着像对的，PG 却**永远
不会去那里找**。显式写回 `share` 才得到 `share/extension/pgroonga.control`
这一真实 PG 扩展布局。

### 2.5 运行期发现：`extension_control_path` + `dynamic_library_path`

产物既然不在 PG 安装目录里，就必须靠集群参数把两处发现路径指过来：

```
extension_control_path = '<pkg>/share:<pg>/share/postgresql'
dynamic_library_path   = '<pkg>/lib:<pg>/lib/postgresql:$libdir'
```

⚠️ **这两个参数的语义不一样，写法也不一样**：

- `extension_control_path` 收的是**基目录**：PG 18 的
  `get_extension_control_directories()`（`src/backend/commands/extension.c`）
  对列表中**每一个不是字面量 `$system` 的元素**都会再拼一层 `/extension`：

  ```c
  if (strcmp(piece, "$system") == 0)
      mangled = substitute_path_macro(piece, "$system", system_dir);
  else
      mangled = psprintf("%s/extension", piece);
  ```

  紧接着 `parse_extension_control_file()` 里还有一条断言
  `Assert(strcmp(control->control_dir + strlen(control->control_dir) - strlen("/extension"), "/extension") == 0);`
  —— PG **断言**解析出来的目录必须以 `/extension` 结尾。所以这里要写
  `<pkg>/share`、而不是 `<pkg>/share/extension`；写了后者，PG 会去找
  `<pkg>/share/extension/extension/pgroonga.control`，于是 psql 报
  `ERROR:  extension "pgroonga" is not available` / `HINT:  The extension
  must first be installed on the system where PostgreSQL is running.`
  （CI #71459 的失败即此：布局断言 13/13 全过、`.control` 明明躺在
  `<pkg>/share/extension/` 下，CREATE EXTENSION 却说找不到）。
  `<pg>/share/postgresql` 必须保留，否则连 `plpgsql` 都找不到（initdb 会失败）。
  想直接写 `<pg>/share/postgresql/extension` 也行——那就必须写成字面量
  `$system`，由 PG 自己展开（`get_share_path(my_exec_path) + "/extension"`），
  但显式给基目录不依赖可执行文件位置推导，更稳。
- `dynamic_library_path` **不**补任何后缀，直接就是目录列表；`$libdir` 是 PG 的
  运行时变量，指向**正在运行的** PG 的 pkglibdir。

**这两个参数落在 `$PGDATA/postgresql.auto.conf`，写入时机必须在 `initdb` 之后**：
`initdb` 拒绝在非空目录里建集群（`directory "..." exists but is not empty`），
而它自己会往 `$PGDATA` 里写 `postgresql.conf` / `pg_hba.conf` / `base/`。
PG 读配置的顺序是 `postgresql.conf` → `postgresql.auto.conf`，后追加即生效
（`ALTER SYSTEM` 改的也是这个文件）。先写 auto.conf 再 initdb，第一步就挂 ——
CI #71436 的 `initdb 失败 (exit 1): ... exists but is not empty` 正是这个。
仓内 `archives/p/postgresql-topn/2.7.0` 的 test_package 用的是同一顺序
（makedirs → initdb → 追加 auto.conf → pg_ctl start），可直接对照。

**为什么 `pgroonga.control` 里的 `module_pathname = '$libdir/pgroonga'` 不用改**：
PG 18 的 `load_external_function` 对「简单名」——`$libdir/` 之后不再出现目录
分隔符——会剥掉前缀，把裸名交给 `dynamic_library_path` 搜索，再依次尝试
`name` 与 `name + DLSUFFIX`。所以只要 `dynamic_library_path` 里有
`<pkg>/lib`，`$libdir/pgroonga` 就能解析到 `<pkg>/lib/pgroonga.so`，
无需打补丁改写 control 文件。

### 2.6 包内 ELF 必须重签名，否则 `dlopen` 拿 EPERM（E077）

CI #71492（build 62266）的失败类别被标成「测试失败」，但 14 条行为断言全部
倒在同一条上：

```
psql:.../assert_pgroonga.sql:21: ERROR:  could not load library
  ".../p/lib/pgroonga.so": Error loading shared library
  .../p/lib/pgroonga.so: Permission denied
```

`Permission denied` 不是文件权限、也不是 `noexec` 挂载，而是**鸿蒙内核拒绝
装载没有有效 `.codesign` 段的 ELF**（E077）。这里加载者是 PostgreSQL 的
`dlopen`（`load_external_function`），路径与 `execve` 无关——所以「产物是库、
不产生可执行文件」并不等于不用签名。

`package()` 末尾追加 `_sign_package_elfs()`：对包内所有真实 ELF（`lib/**` 下
`*.so*` 与 `bin/`）先 `llvm-objcopy --remove-section .codesign` 去掉可能陈旧的
签名段，再 `binary-sign-tool sign -inFile … -outFile … -selfSign 1` 就地重签，
最后补上可执行位。版本化 `.so` 的软链要跳过（否则对同一目标重复签），
`_is_elf()` 用 4 字节魔数判定。做法与仓内 `xxhash/0.8.3`、`zstd/1.5.7.1` 一致。

判据提醒：CI 报「测试失败 / 上游官方测试未通过」时先看日志里的 **errno 文本**——
`Permission denied` + `.so` 路径 ⇒ E077 签名问题，改配方重签即可，不是库的缺陷。

### 2.7 groonga 的插件目录是编译期烘焙的

`libgroonga.so` 里硬编码的插件目录是构建机路径（实测
`/storage/Users/currentUser/.conan2/p/b/groonf04c74dc6be8e/p/lib/groonga/plugins`），
设备上不存在。运行期用 `GRN_PLUGINS_DIR=<pkg>/../groonga/lib/groonga/plugins`
覆盖即可（test_package 的 `_groonga_plugins_dir()` 沿依赖图找）。

### 2.8 `requires(..., run=True)`：SHARED 包会把静态依赖整条闭包挤出运行期

CI build #62306（PR #11628，2026-09-27）的失败长这样：

```
psql:.../assert_pgroonga.sql:21: ERROR:  could not load library
  ".../p/lib/pgroonga.so": Error loading shared library libgroonga.so.0:
  (needed by .../p/lib/pgroonga.so)
```

`libgroonga.so.0` 明明躺在 `groonga/16.0.8` 包里（`<groonga>/lib/`），却在
LD_LIBRARY_PATH 上找不到。日志里真正的线索是 test_package 图的一段：

```
======== Computing necessary packages ========
Requirements
    pgroonga/4.0.8:9b96... - Cache
Build requirements
    postgresql/18.3:01d9... - Cache
Skipped binaries
    groonga/16.0.8, libxxhash/0.8.3, lz4/1.10.0, msgpack/7.0.1, zlib/1.3.1.1
```

**根因是 Conan 的 trait 传播规则，不是环境。**

1. `pgroonga` 的 `package_type = "library"` + `default_options = {"shared": True}`
   ⇒ `PackageType.SHARED`。
2. `requires.py:transform_downstream()` 对「SHARED 包 → 它的依赖」这一类边，
   一律把下游 require 压成 `Requirement(ref, headers=False, libs=False,
   run=require.run)`（SHARED 的实现代码已经静态链好，消费侧确实不需要它的
   headers/libs —— 这是对 **STATIC 依赖**正确的假设）。
3. 而 `GroongaConan` 声明的是 `package_type = "library"` +
   `default_options = {"shared": False}` ⇒ `PackageType.STATIC`，于是
   `process_package_type()` 走 `set_if_none("_run", False)`
   → 这条 require 的 `run` 是 **False**。
4. 两者相乘：`headers=False`、`libs=False`、`run=False`
   ⇒ `Requirement.files` 为假；`graph_binaries._skip_binaries()` 的
   `deps_required = {… if req.files or (req.direct and is_consumer)}`
   于是收不到它，groonga 及其整条下游闭包全被标成 `BINARY_SKIP`。
5. `installer.py` 对 `BINARY_SKIP` 直接 `continue`，`set_base_package()` 永不调用
   ⇒ 测试配方里 `dep.package_folder is None`，`_collect_libdirs()` 的
   `if not pkg_folder: continue` 把它们全部丢掉，LD_LIBRARY_PATH 只剩下
   `<pgroonga>/lib` 与 `<postgresql>/lib`。实测日志：
   `LD_LIBRARY_PATH = .../pgroo41f44267abc28/p/lib:.../postgfee07d5886c8f/p/lib`。

**但 groonga 实际上是个 SHARED 包**：`conaninfo.txt` 写着 `shared=False`，
包内却只有 `libgroonga.so` / `libgroonga.so.0` / `libgroonga.so.0.0.0`
（`conanmanifest.txt` 里 `.a` 计数为 0），`libgroonga.so.0` 的 DT_NEEDED 是
`libc++_shared.so` + `libc.so`（lz4/zlib 已静态链入）。也就是说第 2 步的前提
在 groonga 这里**不成立**——pgroonga.so 的 DT_NEEDED 里真的写着
`libgroonga.so.0`，运行期必须能找到它。

**修法**：把这条 require 显式标成运行期依赖。

```python
self.requires("groonga/16.0.8", run=True)
```

`run=True` 让 `req.files` 为真 → groonga 回到 `deps_required` → 不再被
`Skipped binaries`、`package_folder` 有值、`_collect_libdirs()` 能把
`<groonga>/lib` 加进 LD_LIBRARY_PATH（顺带也让使用者的 `conanrun.sh` 带上它，
否则消费 pgroonga 的自己写的扩展会撞同一堵墙）。语义上没有任何牵强：
DT_NEEDED 里既然有它，它就是运行期依赖。

`lz4` / `zlib` 不必加：groonga 包内没有 `.a`，而 `libgroonga.so.0` 的
DT_NEEDED 只有 libc/libc++ —— 它们是静态链进 `libgroonga.so` 的。
`msgpack` / `libxxhash` 同理（`conan list` + 下载后实测包内只有
`libmsgpack-c.a` / `libxxhash.a`，无 `.so`）。

**通用教训**：在 Conan 2 里，「SHARED 包的依赖全被标记 skip」是**默认**行为，
只要那些依赖被声明成 STATIC。判定一个包是不是真 STATIC，不能只看
`conaninfo.txt` 的 `shared` 值——`shared=False` 的配方照样可能产出并只产出
`.so`（groonga 就是）。要看**包内实际装了什么**（`conanmanifest.txt` 里
`.a` / `.so` 的分布）+ **消费者产物的 DT_NEEDED**，两者对不上时就该在消费侧
用 `run=True` 把它钉回运行期闭包。

### 2.9 依赖的 `.so` 符号链接要在设备上物化（E073）

补上 2.8 之后 CI build #62346（同一天，PR #11628）仍然报同一句话：

```
psql:.../assert_pgroonga.sql:21: ERROR:  could not load library
  ".../p/lib/pgroonga.so": Error loading shared library libgroonga.so.0:
  (needed by .../p/lib/pgroonga.so)
```

但这次 `Skipped binaries` 段已经消失、`groonga/16.0.8: Already installed!`，
LD_LIBRARY_PATH 也确实变成了

```
.../p/pgroof3d3e0ba76486/p/lib:.../p/groon3529a0cd50dcf/p/lib:.../postgfee07d5886c8f/p/lib
```

**目录已经在搜索路径上了，同一个错误却一字未变** —— 这说明问题不是「找不到」，
而是「找到了但加载不了」。三种报错的鉴别要点：

| 现象 | 含义 |
| --- | --- |
| `... : No such file or directory` | 搜索路径上没有 |
| `... : Permission denied` | 有，但 ELF 没有有效 `.codesign` 段（E077 未签名） |
| `... : `（strerror 为空） | **有，但加载器解析不到实际库文件** —— 符号链接（E073） |

**根因是符号链接。** `groonga/16.0.8` 包内的三个名字只有一个是真的：

```
lib/libgroonga.so:      64b2e5883e0aaeb1f2afa7fe9a7c579e == md5("libgroonga.so.0")
lib/libgroonga.so.0:    33c7fb34c1fb5cd7565f0a1bab68c24d == md5("libgroonga.so.0.0.0")
lib/libgroonga.so.0.0.0: 2cf768df127a1b34bdf4314faf28563e   ← 唯一的真文件
```

`conanmanifest.txt` 对符号链接记的是**目标字符串**的 md5（Conan 用这种方式
在 manifest 里表达链接关系），所以前两条一眼可判是链接。而 pgroonga.so 的
DT_NEEDED 恰恰是 `libgroonga.so.0` 这个**链接名**，设备上 dlopen 时命中链接、
HMDFS 解析不到 `libgroonga.so.0.0.0`。

反向对照：`sdl12-compat` 的 `libSDL-1.2.so.0` 在 manifest 里记的是真文件 md5
（不是任何目标字符串的 md5），它在设备上加载正常 —— 同一套判定法。

排除 E077（签名）的判据：`libgroonga.so.0.0.0` 有 `.codesign` 段（type=1、
4096 字节、非零字节 75），与已知能加载的 `libSDL-1.2.so.0`（非零 76）、
`libpq.so.5`（非零 76）同类；若真是签名问题，报的会是
`Permission denied`（见 2.6）。

**修法**：在 test_package 里把各依赖 libdir 顶层的符号链接展开成真文件副本，
放进一个 staging 目录并**置于 LD_LIBRARY_PATH 最前**，让加载器命中的是普通文件
（`_stage_symlinked_libs()`；副本按字节复制，自带原签名，不需要重新签）。
被加载的是依赖包而不是本包，所以改不了 groonga 的配方，只能在消费侧
（test_package）补 —— 与 `libsigc/2.12.1`、`libsigc-2/2.12.2`、
`fluidsynth/2.5.7`、`libxft/2.3.8` 的处置同属 E073。

**通用教训**：依赖包里凡是 `conanmanifest.txt` 里 md5 等于「某个兄弟文件名
字符串的 md5」的条目，就是符号链接；在 HMDFS 上这类名字一旦进了 DT_NEEDED，
就必须在消费侧物化。别被「文件明明在那儿」骗过去 —— 要看的是
`Error loading shared library ...` 冒号后面那截 strerror 有没有内容。

## 3. 上游回归套件

### 3.1 三档口径

| 口径 | `sql/**.sql` | `expected/**.out` |
|------|--------------|-------------------|
| **A. 默认分支 `main` 朴素扫描（声明值）** | **1608** | 1658 |
| B. 钉版 4.0.8 tarball 朴素扫描 | 1600 | 1650 |
| C. 本 test_package 实跑 | **1598** | — |

A − B = 8，逐文件核对是**上游 4.0.8 之后新增**的两组用例（main 上同时有
对应的 `.out`，钉版里一组都没有；反向差集为空，钉版没有任何 main 上不存在
的用例）：

```
function/physical-table-names/{nonchildren,nonexistent,nonpartition,
                               range-partition,too-long-prefix}   5
index-scan/view-statistics/user-indexes/{bitmapscan,indexscan,seqscan}  3
```

B − C = 2 = `regress-skip.txt` 里逐条写明原因的 2 例（见 3.3）。

1600 例的 group 分布（钉版，17 个顶层分类，最深 9 层）：

| group | 数 | group | 数 |
|-------|----|-------|----|
| full-text-search | 683 | jsonb | 149 |
| regexp | 237 | compare | 60 |
| term-search | 223 | compatibility | 54 |
| function | 156 | variable | 13 |
| semantic-search | 9 | custom-scan | 4 |
| index-only-scan | 4 | groonga-function | 2 |
| int4-array | 2 | column-name | 1 |
| index-scan | 1 | reindex | 1 |
| vacuum | 1 | | |

### 3.2 上游入口用不了，但用例集合一点没少

上游 `-Dtest=true`（meson.build:585-586）会 `find_program('ruby')` 找 test/prepare.rb，用 ruby 生成
pg_regress schedule。OHOS 没有 ruby，构建期因此显式 `-Dtest=false`。

但 `prepare.rb` 全文只有三件事（38 行）：

```ruby
Find.find(sql_dir) do |entry|                 # 递归遍历 sql/
  if File.directory?(entry)
    FileUtils.mkdir_p("results/#{relative}")  # 每个目录预建 results/<dir>
  elsif File.file?(entry) && entry.end_with?(".sql")
    output.puts("test: #{relative.sub_ext('')}")   # 每例一行 test: <相对路径>
  end
end
```

`test_package/conanfile.py:_write_schedule()` 用 Python 十行等价复刻，
**刻意不做任何"顺手过滤"**：不筛 oracle 是否存在、不按 group 挑。唯一的删减
就是 `regress-skip.txt` 的 2 例。理由很实际——如果在这里静默丢掉"找不到
oracle"的用例，就会得到"跑得全绿但用例集缩水"的假绿，而这正是评审要抓的。

pg_regress 的其余参数逐条对齐上游 `meson.build:628-636`：`--bindir` /
`--dlpath` / `--inputdir` / `--outputdir` / `--launcher test/short-pgappname`
/ `--load-extension pgroonga` / `--schedule`。唯一**必须**多出的是
`--host/--port/--user/--dbname`：仓库打包的 PG 定义了 `HAVE_NO_UNIX_SOCKETS`，
pg_regress 不能用 `--temp-instance`，只能连一个已启动的 TCP 集群。

逐文件核对：`sql/` 与 `expected/` 里没有任何一处引用 `application_name` 或
`pg_stat_activity`，所以 `short-pgappname`（只把 `PGAPPNAME` 钉成 `pg_regress`）
不影响断言。

### 3.3 排除的 2 例：groonga 的**外部**插件

| 用例 | 需要 | OHOS groonga/16.0.8 |
|------|------|---------------------|
| `function/tokenize/metadata` | `TokenizerMecab` | ❌ 未编入 |
| `full-text-search/text/options/token-filters/custom` | `TokenFilterStem` | ❌ 未编入 |

groonga 的插件式 tokenizer / token filter 是**独立构建产物**：Debian/Ubuntu
上分别是 `groonga-tokenizer-mecab` / `groonga-token-filter-stem` 两个包，不属于
groonga 本体。OHOS 的 `groonga/16.0.8` 包内 `lib/groonga/plugins/` 只有

```
functions/  query_expanders/tsv.so  suggest/suggest.so  token_filters/stop_word.so
```

既无 `tokenizers/mecab` 也无 `token_filters/stem`，因此这 2 例在设备上必然拿到
groonga 的 `unsupported tokenizer/filter` 报错，与 pgroonga 适配无关。
逐文件 grep 确认 `sql/` 下 `TokenMecab` 与 `TokenFilterStem` **各只命中 1 处**；
其余用例用到的 `TokenNgram` / `TokenBigram` / `NormalizerNFKC*` 都是 groonga
内置实现（随包提供，不需要插件）。

需要恢复时：把 groonga 的 mecab/stem 插件放进 `lib/groonga/plugins/` 并设置
`GRN_PLUGINS_DIR`，再把 `regress-skip.txt` 里对应两行删掉即可。

### 3.4 oracle 为什么可信

上游 `.github/workflows/linux.yml` 的 CI 矩阵用**同一份** `expected/` 在
PostgreSQL 14/15/16/17/18/19 上全绿（:38-52），说明该 oracle 集合本身跨 PG
版本稳定；`expected/` 下的 50 个 `_1/_2` 备用 oracle 专门覆盖 guc / 版本 /
环境差异，例如 `function/language-model-vectorize/huggingface` 与
`semantic-search/*` 会在未设置 `PGRN_LANGUAGE_MODEL_TEST` 时提前 `\quit`，由
`_1.out` 兜底。本包**刻意不设**该变量，让这批用例走自动跳过分支而不是真去
下载语言模型。

test_package 另外把集群参数对齐上游 CI 的 `postgresql.conf` 追加项：

```
enable_partitionwise_join = on
max_prepared_transactions = 1
random_page_cost          = 0
```

这三条直接决定 `EXPLAIN (COSTS OFF)` 类用例的计划形状，不设就必然 diff。

## 4. 消费者测试（test_package）

### 4.1 静态布局层（12 条）

- 7 个 shared module 都在**本包** `lib/`（上游 `name_prefix: ''`，所以就叫
  `<name>.so`；`name_suffix` 在 OHOS 上取 `so`）；
- `share/extension/` 下 `pgroonga.control` / `pgroonga--4.0.8.sql` /
  `pgroonga_database.control` / `pgroonga_database--4.0.8.sql` 齐备；
- `pgroonga.so` 是 aarch64 ELF 共享对象（读 ELF header 的 `e_machine`，
  判 `0xB7` = `EM_AARCH64`）；
- **反向断言**：`<pg>/lib/postgresql/pgroonga.so` 与
  `<pg>/share/postgresql/extension/pgroonga.control` **不存在** —— 证明产物
  落点确实是本包，靠 `extension_control_path` / `dynamic_library_path` 被发现，
  而不是走"装进 PG 安装目录"那条不可重定位的捷径。

### 4.2 行为断言层（`assert_pgroonga.sql`，14 条）

每条通过后打印一行 `ASSERTION_OK: <id>` 供 CI 日志取证；`psql -v
ON_ERROR_STOP=1` 保证任一断言失败即非零退出。

| id | 覆盖点 |
|----|--------|
| A1 | `CREATE EXTENSION pgroonga` —— 本适配最核心的一条（`$libdir` 重定位） |
| A2 | `pg_extension.extversion = 4.0.8` |
| A3 | `pgroonga_escape(292929::int4)`（C 符号 `pgroonga_escape_int4`）→ `292929` —— C 函数真实执行，证明模块已 dlopen 且符号解析成功。**上游 4.0.8 没有 `pgroonga_version()`**（`data/pgroonga.sql` 全文无 version 函数），版本一致性由 A2（`pg_extension.extversion`）与 A4（status 里的 libgroonga 版本号）承担；期望值取自上游 oracle `expected/function/escape/int4.out` |
| A4 | `pgroonga_command('status')::jsonb->0->>0 = 0` 且携带 `libgroonga` 版本号（必须走 `jsonb` 的 `->>`：PG 里 `json` 不能 `::int`，实测 `cannot cast type json to integer`） |
| A5 | 路径卫生：存在 `probin = '$libdir/pgroonga'` 且**没有**任何 `probin` 含绝对路径 |
| A6 | v1 全文检索 `content &@ 'Groonga'` → `{2,3}` |
| A7 | 查询语法 `content &@~ 'rdbms OR engine'` → `{1,2}` |
| A8 | `pgroonga_score(tableoid, ctid) > 0`（索引扫描路径下） |
| A9 | v2 词项前缀 `pgroonga_text_term_search_ops_v2` + `name &^ 'PGro'` → `{PGroonga}` |
| A10 | jsonb v2 `pgroonga_jsonb_ops_v2` + `record &@ 'postgresql'` → `{1,3}`（**不**用 `'groonga'` 期望 `{2,3}`：第 3 行的 `PGroonga` 是不可再分的词，CI #62641 实测只回 `{2}`；`postgresql` 与分词器无关地命中两行，且第 3 行只靠 content 命中，顺带证明 jsonb 索引检索的是嵌套字符串值） |
| A11 | `pgroonga_highlight_html` 产出 `<span class="keyword">RDBMS</span>` |
| A12 | `pgroonga_query_extract_keywords('Groonga PostgreSQL')` → `{Groonga,PostgreSQL}` |
| A13 | `unnest(pgroonga_tokenize(..., 'tokenizer', 'TokenNgram'))` 恰 14 片、首片 `Th` 且 `force_prefix_search=false`（内置分词器，非插件；返回类型是 **token 数组**，不 `unnest` 直接 count 只会数到 1 个数组值） |
| A14 | `DROP EXTENSION pgroonga CASCADE; CREATE EXTENSION pgroonga;` 后 `extversion` 与 `pgroonga_escape(292929::int4)` 仍正确（可逆性：不依赖一次性安装副作用） |

A5 值得单独说：它同时钉住"可重定位"这件事的两个方向——`probin` **必须**仍是
`$libdir/pgroonga`，且**不得**出现 `/...` 或 `a/b/c` 形式的绝对路径。谁要是把
构建机路径烘焙进 catalog，这条会立刻红。

### 4.3 上游回归层

`pg_regress` 连同一个集群跑 1598 例；解析 `^\s*test\s+(\S+)\s+\.\.\.\s+(ok|FAILED)$`
统计通过/失败，失败时把 `regression.diffs` 尾部打到控制台，并 `raise`。
同时输出机读汇总行：

```
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...}
HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"pg_regress",
                           "discovered":1600,"executed":1598,"passed":1598,...}
```

## 5. 复现命令

```bash
# 构建 + 全量门禁（test_package 会自动 initdb + 起 TCP 集群 + 跑 1598 例回归）
conan create archives/p/pgroonga/4.0.8 -pr:h=ci/conan/profiles/ohos-aarch64 \
                                      -pr:b=ci/conan/profiles/ohos-aarch64

# 只想看上游回归
conan test archives/p/pgroonga/4.0.8/test_package pgroonga/4.0.8@ \
            -pr:h=ci/conan/profiles/ohos-aarch64
```

## 6. 随包内容

```
lib/*.so                                              7 个 shared module
share/extension/{pgroonga,pgroonga_database}.control
share/extension/{pgroonga,pgroonga_database}--4.0.8.sql
upstream/{sql,expected,test}/                          上游回归套件（供 test_package）
licenses/COPYING
```

## 7. 参考链接

- 上游文档：https://pgroonga.github.io/
- 上游回归入口：`test/prepare.rb`、`meson.build:585-586`（ruby）、`meson.build:628-636`（pg_regress 参数）
- 同仓库先例：`archives/p/postgresql-topn/2.7.0`（PG 扩展 + 真集群测试的模板）
