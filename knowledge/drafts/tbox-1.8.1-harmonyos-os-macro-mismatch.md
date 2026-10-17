# tbox 1.8.1 在 HarmonyOS 上的三个构建口径缺陷（草稿，预留条目 E581）

- **软件**：tbox 1.8.1（https://github.com/tboox/tbox）
- **构建系统**：上游自带 POSIX `configure`（xmake.sh 前端）+ 生成 Makefile，无需 xmake 二进制、无需 autotools
- **平台**：HarmonyOS PC / aarch64（`uname` = `HarmonyOS aarch64`），编译器 `clang 15.0.4`
  (`/data/service/hnp/bin/clang`，target `aarch64-unknown-linux-ohos`)
- **状态**：DRAFT（预留编号 E581）

## 现象

设备原生 `./configure --kind=shared … && make` 首次失败于：

```
src/tbox/platform/bsd/filelock.c:102:73: error: use of undeclared identifier 'LOCK_EX'
src/tbox/platform/bsd/filelock.c:102:12: warning: call to undeclared function 'flock'
```

## 根因

1. **平台宏改名漏改消费者**：configure 按 `uname` 认定宿主为 harmonyos，在生成的
   `tbox.config.h` 里写 `#define TB_CONFIG_OS_HARMONYOS 1`；而
   `src/tbox/platform/bsd/filelock.c` 第 27 行的 include 守卫仍是旧名
   `TB_CONFIG_OS_HARMONY`（全库唯一一处）。守卫不成立 → 走 `#include <fcntl.h>`，
   该头不声明 `flock`/`LOCK_EX`/`LOCK_SH`/`LOCK_NB` → 编译失败。
   设备实测 `<sys/file.h>` 存在且 `flock(0, LOCK_EX|LOCK_NB)` 可用，因此修守卫即可。
2. **汇编符号被 `.hidden`**：`src/tbox/prefix/arm64/prefix.S` 的 `function` 宏对
   export / 非 export 两个分支都输出 `.hidden`，所以 shared 版 `libtbox.so`
   **不导出** `tb_context_make`/`tb_context_jump`（`llvm-readelf --dyn-syms` 无此二符号），
   上游 demo 的 `platform_context` 用例在链接期报 undefined symbol。
   常规 C API（含 `tb_coroutine_*`）不受影响。
3. **`--info=y` 是空开关**：同一批 `--float=y`/`--force_utf8=y`/`--hash=y`/`--xml=y` 等
   都写入了 `tbox.config.h`，只有 info 没有生成 `TB_CONFIG_INFO_HAVE_VERSION`，
   产物里因此没有 `tb_version()`。
4. **shell 前端完全没有包探测**：`add_packages()`/`has_package()` 只存在于 `xmake.lua`。
   `--database=y` 于是编出一个**没有任何后端**的 database 模块：
   `TB_CONFIG_PACKAGE_HAVE_SQLITE3` 永不置位，`add_files "database/*.c"` 也不含 `impl/`，
   `database/impl/sqlite3.c` 根本不参与编译，直到链接期才报
   `undefined symbol: tb_database_sqlite3_probe / _init`。
   另：该前端里在 target 之外调用 `add_includedirs`/`add_links` 会把条目挂到空 target 上，
   接线必须写进 `target "tbox"` / `target "demo"` 块内。

## 处置

- 最小补丁（1 行）：`filelock.c` 守卫追加 `|| defined(TB_CONFIG_OS_HARMONYOS)`。
  不改 configure 生成宏的名字——新名才是 1.8.x 的口径。
- 配方固定 `--kind=static`（上游默认 kind 也是 static），并显式传
  `--plat=harmonyos --arch=arm64 --toolchain=envs`，用注入的 `$CC/$CXX/$AR`
  把编译器来源钉死在 Conan conf 上。
- 消费者测试用已安装头里的 `TB_VERSION_MAJOR/MINOR/ALTER` 做版本自证，不用 `tb_version()`。
- database 模块：配方 `requires("sqlite3/3.49.1")`，补丁 0003（库）/0001（demo）在 target 内
  读取配方注入的 `TB_SQLITE3_INCLUDEDIR`/`TB_SQLITE3_LIBDIR`，
  `add_defines "TB_CONFIG_PACKAGE_HAVE_SQLITE3=1"` + `add_includedirs` +
  `add_files "database/impl/sqlite3.c"` + `add_linkdirs` + `add_links "sqlite3"`。

## 验证

- `conan create`（ohos-aarch64 / clang 15.0.4，含 sqlite3/3.49.1 依赖）干净源码构建通过，
  干净轮 `apply_patch=3`，test_package 10/10。
- 设备原生 `--demo=yes` 构建出 **160** 个上游用例（源码宏数与框架注册数一致）并逐个执行；
  结果与逐项归因见 PR 正文。
- `database_sql` 无参调用是**空洞通过**（`tb_database_sql_init(NULL)` 返回空 → `return 0`，
  没跑任何 SQL）；按上游用法 `file://<db> blobdata` 实跑 rc=0（真实建表/插入/事务/查询）。

## 复用价值

任何“发行版把平台名从 X 改成 XY、但源码里仍有旧名消费者”的 C 项目都会以同样的
`undeclared identifier` 形态失败；判据是**先找生成宏的实际拼写，再比对各消费者**，
不要按“缺头文件/缺系统调用”去排查。第 2 条提示：看到链接期 undefined symbol 时，
先分清符号是 C 函数还是汇编内核，后者可能被上游 `.hidden` 固化而无法在 shared 包里导出。
第 3/4 条提示：**不要相信构建前端的 `--help`**——开关"看起来存在"不等于"真的生效"；
对每个开关都要回到生成的 config 头或编译命令行上验证一次。
