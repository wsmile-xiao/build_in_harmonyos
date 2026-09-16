# ol (Otus Lisp)

纯函数式、可嵌入的 Scheme 方言解释器（Otus Lisp），纯 C（C99）实现、单文件虚拟机、
无第三方依赖。产物同时覆盖命令行解释器与嵌入式（embedding）场景。

## 功能概述

- `bin/ol`：内嵌 REPL fasl 的解释器，可直接执行 `.scm` 脚本或进入 REPL
- `bin/olvm`：剥离符号的独立虚拟机（供脚本/测试批量驱动）
- `lib/libol.so` + `include/ol/ol.h`、`include/ol/vm.h`：可嵌入的 VM API
  （`OL_new` / `OL_eval` / `OLVM_*`），第三方程序可把 Ol 作为脚本引擎链接进自身
- `lib/ol/`：Ol 标准库（`libraries/**.scm|*.lisp`）与 REPL fasl，运行期由 `OL_HOME` 定位
- 附带 `share/man/man1/ol.1.gz` 手册页

## OHOS 适配

- 构建系统是 plain GNUmakefile：配方传 `CC`（取 `tools.build:compiler_executables`）、
  `UNAME=Linux` 与编译期 `PREFIX`，不传 `CFLAGS`（GNU make 命令行变量会整段覆盖上游
  `CFLAGS +=`）。`UNAME=Linux` 是必须的：鸿蒙 `uname -s` 返回 `HarmonyOS`，
  会跳过上游 Linux 分支从而丢掉 `-Xlinker --export-dynamic`，运行期 FFI 取不到
  `OLVM_ffi` 符号
- 上游 `make install` 依赖 coreutils 的 `install(1)`，OHOS 未提供该工具，
  因此 `package()` 按上游 install 目标的布局自行落盘
- 上游 `olvm` 目标链接后执行 `strip`，剥离后的 ELF 在鸿蒙内核上被拒绝执行
  （`Operation not permitted`，rc=126）；配方对 `bin/` 下 ELF 用 `binary-sign-tool`
  重新自签名，`libol.so` 保持 hnp clang 自带的链接器签名不重签
- 运行期 `OL_HOME` 由 `package_info()` 的 `runenv`/`buildenv` 导出为 `<包>/lib/ol`，
  编译期 `PREFIX` 保持上游默认 `/usr`，包在缓存/任意前缀下均可重定位使用

## 依赖关系

- 编译依赖：无（仅 OHOS clang 15 工具链与其 sysroot）
- 运行依赖：无（`libol.so` 仅依赖 OHOS libc/musl）

## 参考资料

- 官网：https://yuriy-chumak.github.io/ol/
- 源码：https://github.com/yuriy-chumak/ol
- 上游版本：2.7
