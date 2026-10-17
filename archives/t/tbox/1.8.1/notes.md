# tbox 1.8.1 适配笔记

## 编译环境

- 构建系统: makefile（上游自带 POSIX `configure`，xmake.sh 前端；无需 xmake 二进制、无需 autotools）
- 编译日期: 2026-09-17
- 平台: HarmonyOS PC / aarch64（`uname` = `HarmonyOS aarch64`）
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`）
- 状态: built

## 编译步骤

```sh
# 官方 tag 归档（release v1.8.1 未上传 assets）
# https://github.com/tboox/tbox/archive/refs/tags/v1.8.1.tar.gz
# sha256 48284c1f1f6e4e74ce1b4d2447c3141fdfdd3a20ef1cb30fc2f1021149227fdb

TB_SQLITE3_INCLUDEDIR=<sqlite3>/include TB_SQLITE3_LIBDIR=<sqlite3>/lib \
CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ AR=/data/service/hnp/bin/llvm-ar \
  "$CONFIG_SHELL" ./configure \
    --plat=harmonyos --arch=arm64 --toolchain=envs --mode=release --kind=static \
    --small=no --micro=no --float=y --force_utf8=y \
    --charset=y --hash=y --xml=y --object=y --regex=y --coroutine=y \
    --database=y --exception=y --zip=no --demo=no --prefix=/
make -j1
make install DESTDIR=<package_folder>     # --prefix=/ + DESTDIR 组合
```

- `TB_SQLITE3_INCLUDEDIR` / `TB_SQLITE3_LIBDIR` 由配方从 `self.dependencies["sqlite3"]`
  的 `cpp_info` 取出后注入，供补丁 0003（库）与补丁 0001（demo）接线 sqlite3 后端。
- `--toolchain=envs` 让 configure 采用注入的 `$CC/$CXX/$AR`，编译器来源钉死在 Conan conf（R33），不依赖 PATH 顺序。
- `--plat=harmonyos --arch=arm64` 显式指定目标，避免由宿主 `uname` 隐式决定。
- `--prefix=/` + `make install DESTDIR=<pkg>` 才是正确的安装路径组合：Makefile 的
  `INSTALLDIR` 会把 PREFIX 去首斜杠后拼到 DESTDIR 后面，传绝对 prefix 会多出一层路径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `platform/bsd/filelock.c` 报 `use of undeclared identifier 'LOCK_EX'` / `call to undeclared function 'flock'` | configure 按 `uname` 生成 `TB_CONFIG_OS_HARMONYOS`，该文件第 27 行 include 守卫仍写旧名 `TB_CONFIG_OS_HARMONY`（全库唯一一处），守卫不成立 → 落到 `<fcntl.h>`，其中没有 flock 系列声明 | `patches/0002-src-tbox-platform-bsd-filelock.c.patch`：守卫追加 `\|\| defined(TB_CONFIG_OS_HARMONYOS)`（1 行）。设备实测 `<sys/file.h>` 存在且 `flock/LOCK_EX` 可用 |
| 2 | shared 构建时 demo 链接报 `undefined symbol: tb_context_make / tb_context_jump` | `src/tbox/prefix/arm64/prefix.S` 的 `function` 宏无条件输出 `.hidden`，shared 库不导出汇编内核符号 | 默认 `--kind=static`（上游默认 kind 也是 static）；`shared` 选项保留但仅对不使用低层 `tb_context_*` 的消费者可用 |
| 3 | `tb_version()` 在产物中不可用 | xmake.sh 前端里 `--info=y` 不生效（同批 `--float=y`/`--force_utf8=y`/模块开关都生效，只有 info 未生成 `TB_CONFIG_INFO_HAVE_VERSION`） | 配方不下发 `--info`；消费者测试改用已安装头的 `TB_VERSION_MAJOR/MINOR/ALTER` 做版本自证 |
| 4 | `conan create` 报 `BadZipFile: File is not a zip file` | Conan `get()` 按 URL 后缀判定归档格式，`codeload.../v1.8.1` 无后缀被当 zip | 改用仓库主流形态 `https://github.com/tboox/tbox/archive/refs/tags/v1.8.1.tar.gz`（实测与 codeload 字节、sha256 完全一致） |
| 5 | `object_jcat` 段错误（rc=139） | 上游 demo 的长选项解析路径缺陷：`--file <path>` / `--file=<path>` 崩溃，同一用例 `-f <path>` 正常（`object_json` 等其余 object 用例全 PASS） | 非配方问题；按逐用例证据记录（见 reports/） |
| 6 | `--database=y` 时链接报 `undefined symbol: tb_database_sqlite3_probe / _init` | **shell 构建前端没有包探测**：`add_packages()/has_package()` 只存在于 `xmake.lua`，`xmake.sh` 里没有对应实现，因此 `TB_CONFIG_PACKAGE_HAVE_SQLITE3` 永不置位、`database/impl/sqlite3.c` 也不会被加入编译（`add_files "database/*.c"` 不含 `impl/`） | 补丁 0003（库）+ 0001（demo）：在 target 内读 `TB_SQLITE3_INCLUDEDIR/TB_SQLITE3_LIBDIR`，据此 `add_defines/add_includedirs/add_files database/impl/sqlite3.c/add_linkdirs/add_links`。sqlite3 由配方 `requires("sqlite3/3.49.1")` 提供 |

## 源码修改

> 补丁编号的权威映射（`conanfile.py` 的 docstring 里有一处编号笔误：把三处写成了
> 「0001 = filelock、0002/0003 = 两个 xmake.sh」；**以本节与 `conandata.yml` 为准**）：

- `patches/0002-src-tbox-platform-bsd-filelock.c.patch` — 只改
  `src/tbox/platform/bsd/filelock.c` 的 include 守卫，追加新平台宏名，使 HarmonyOS 走
  `<sys/file.h>`。（+1/-1；`git diff` 口径）
- `patches/0003-src-tbox-xmake.sh.patch` — `src/tbox/xmake.sh` 的 `target "tbox"` 内
  接线 sqlite3 后端（+18/-0，补丁头写 +19 是含尾随上下文行）。
- `patches/0001-src-demo-xmake.sh.patch` — `src/demo/xmake.sh` 的 `target "demo"` 内
  同样接线（+12/-0），使上游 demo 套件的 `database_sql` 用例可真实执行；不影响库产物。

三个补丁对干净解包源码逐个 `git apply --check` 均通过，依次应用后与构建工作树逐字节一致；
`src/demo/**.c`（上游测试用例本体）零改动。

## 依赖版本

- `sqlite3/3.49.1`（registry `ohpcd`，`conan install --build=never` 实测可装；
  提供 `include/sqlite3.h` + `lib/libsqlite3.a`）——database 模块的后端。
- 其余模块为内置实现：`charset / hash / xml / object / regex / coroutine / exception`
  （`regex` 走 POSIX `regcomp`）。`zip` 需 zlib，未启用（`--zip` 不门控任何上游用例）。

## 验证结果

见 `reports/test-report.md`（逐用例统计与逐项归因）与 PR 正文。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libtbox.a | 1192748 B | 静态库（`--kind=static`） |
| include/tbox/** | — | 公共头（含生成的 `tbox.config.h`） |
| licenses/LICENSE.md | — | Apache-2.0 |

## 注意事项

- 构建期间唯一改动是上面那 1 行补丁；`configure`/`Makefile`/`tbox.config.h` 都是生成物，不入库（R6）。
- TBox 的 `demo` 二进制是上游测试套件的入口（`g_demo[]` 注册用例，按名字调度），
  带参数与不带参数的调用语义不同；逐用例统计口径见 `reports/test-report.md`。
- 设备与 CI worker 同构（都是 `uname=HarmonyOS` 的 aarch64 + OHOS SDK clang 15），
  因此设备原生构建结果对 CI 有直接参考价值；但设备 PATH 含 `~/.harmonybrew/bin`，
  本配方不依赖该目录的任何工具（只用 clang/ar/make + POSIX shell）。
