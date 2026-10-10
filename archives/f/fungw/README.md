# fungw

## 简介

fungw 是 Tibor 'Igor2' Palinkas 写的轻量可移植 C89 库，作用是**跨语言函数调用网关**：
宿主程序（C）把自己的函数注册进 fungw 上下文，脚本语言（fawk / lua / tcl / python /
perl / mruby / duktape / mujs …）里的代码就能反过来调用这些宿主函数，反之亦然。
它被 pcb-rnd / librnd / sch-rnd / camv-rnd 等 repo.hu 系 EDA 工具用作脚本插件底座。

核心概念：`fgw_ctx_t` 上下文 → `fgw_obj_t` 对象 → 注册在对象上的 `fgw_func_t` 函数，
调用时可以走类型化路径（`fgw_vcall` / `fgw_vcall_in`）也可以走字符串化路径
（`fgw_scall`），实参由 `fgw_arg_conv()` 在 FGW_INT / FGW_LONG / FGW_DOUBLE / FGW_STR
等类型之间自动转换。

## OHOS 适配

### 1.2.2（feat/fungw-1.2.2）

- **构建系统不是 autotools**，是作者自研的 scconfig：根目录 `configure` 只有 51 字节
  （`cd scconfig && make && ./configure "$@"`），由 `*.in` 模板现场生成各子目录 Makefile。
- **CC 注入**：scconfig 自举时用 make 内建变量 `CC`（默认 `cc`）编译 hooks.c，
  OHOS SDK 只提供 clang → 配方从 `tools.build:compiler_executables` 取 `c` 编译器，
  命令前缀 `CC=<clang>`；同时 `./configure` 改用 `sh ./configure`
  （conan 复制源码到 HMDFS 时丢掉 +x 位，直接执行是 exit 126）。
- **禁用 perl 绑定**：scconfig 无 `--with/--without`，语言绑定靠系统探测；
  探测到 `/data/service/hnp/bin/perl` 会开启 perl 绑定（OHOS 无 libperl 可链），
  故显式 `--disable-perl`。保留的 c / fawk / cli 三个绑定代码全部内嵌于上游 tarball。
- **HMDFS 不支持链接**：genht 的兼容别名 `genht_std.a` 用 `ln -s`（make 直接 Error 2），
  安装期的 SONAME 别名用 `sccbox ln -f`（硬链接，静默失败只留下 `.so.X.Y.Z`）。
  对策：先复制出 `genht_std.a`；SONAME 别名与 `lib/puplug/*.so` 在 `package()` 内复制生成。
- **共享库自洽化**：上游 `.so` 链接规则不含 `src_3rd/genht`，留下 `strhash`/`htsp_init`
  等未定义符号，任何消费者链接都会撞 `ld.lld --no-allow-shlib-undefined`。
  用 `make LDFLAGS="-rdynamic -fPIC <genht/*.o>"` 把 genht 目标文件链进 `.so`。
- **补齐头文件**：`libfungw/fungw.h` 直接 `#include <genht/htsp.h>`，但上游 install 不装
  genht 头 → `package()` 补 `include/genht/*.h`。

## 依赖

无 Conan 依赖。genht（`src_3rd/genht`）与 libfawk（`libfungwbind/fawk/libfawk_sc`）
均随上游源码分发。

## 功能验证

- 上游 regression（配方 `build()` 内真实执行，非声明）：
  `./test`、`./test_c`、`./test_custom`、`./multicall`（输出与 `multicall.ref` 逐字比对）、
  `SCRIPT=../doc/example/00_hello/hello.fawk ./test_script` —— **5/5 通过**。
- 消费者测试 `test_package/test_fungw`：初始化上下文 → 注册对象与 C 函数 →
  类型化调用 `fgw_vcall_in` → 字符串化调用 `fgw_scall` → `fgw_arg_conv` 转换 →
  `fgw_dump_ctx` → 释放 —— **9/9 断言通过**。
- `shared=True`（默认）与 `-o shared=False` 两条链路均 `conan create` 通过。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/libfungw.so.1.2.2`（+ `.so.1.2` / `.so.1` / `.so`） | 核心库，SONAME `libfungw.so.1` |
| `lib/libfungw_c.so.1.2.2`（+ 别名） | C 语言绑定（宿主函数注册/调用辅助） |
| `lib/libfungw_fawk.so.1.2.2`（+ 别名） | fawk 脚本引擎（内嵌 libfawk） |
| `lib/libfungw_cli.so.1.2.2`（+ 别名） | cli 绑定 |
| `lib/puplug/*.pup` / `*.mak` / `*.so` | puplug 插件描述与插件库 |
| `include/libfungw/*.h`、`include/libfungwbind/c/fungw_c.h`、`include/genht/*.h` | 公开头文件 |

CMake 消费方式：`find_package(fungw REQUIRED)` + `target_link_libraries(app fungw::fungw)`。

## 注意事项

- 上游 INSTALL 写「暂时没有自动化测试」，实际 `regression/` 下有 5 个测试程序，
  由顶层 `make` 一并构建。
- 源 URL 只有 http 端点（上游站点 443 拒连），按仓内既有口径保留官方源，
  完整性由 sha256 钉住（见 `conandata.yml` 注释）。
- 需要 lua/tcl/python/mruby 等绑定时，须先适配对应语言开发库并去掉 `--disable-*` 开关。
