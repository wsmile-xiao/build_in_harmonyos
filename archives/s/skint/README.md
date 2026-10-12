# skint

SKINT 是 false-schemers 维护的可移植 R7RS-small Scheme 解释器：一个 13K 行
左右的 C 实现，自带精确 GC、正确的尾递归、`call/cc`、`dynamic-wind`、多值返回、
卫生宏系统与库系统。标准库全部内建，不需要任何外部文件即可运行；另外发行包
还带一棵 `lib/` 外置库树，提供 100+ 个 SRFI 的 `.sld` 实现，可按需 `(import)`。

## 包内容

- 解释器：`bin/skint`
- 外置 SRFI 库树：`share/skint/lib/**`（135 个 `.sld` + 少量 `.scm`）
- man page：`share/man/man1/skint.1`
- 许可：BSD-3-Clause

## 用法

```bash
skint                       # 交互 REPL
skint -s hello.scm a b      # 按 SRFI-22 脚本方式执行，a b 传给 (command-line)
skint -e '(map (lambda (x) (* x x)) (list 1 2 3))'
skint -l prelude.scm -e '(main)'
skint -p program.scm        # R7RS 程序模式（文件内自行 import）
```

外置 SRFI 库树通过环境变量 `SKINT_LIBDIRS` 定位：本包用 Conan 的
`runenv_info` 注入 `<包前缀>/share/skint/lib`（`conanrun.sh` /
VirtualRunEnv 生效），因此不把构建期绝对路径编进 ELF，包可重定位。
也可以按次覆盖：`skint -I /some/libdir ...`。

## OpenHarmony 适配要点

- 自包含可移植 C11，零外部依赖（只需要 C 运行时）；`make` 直接编译
  5 个 `.c` 并 `-lm` 链接。
- 不需要源码补丁：`s.h` 的平台分派链在 OHOS clang 上命中
  `__GNUC__ && __linux`（OHOS clang 同时定义 `__GNUC__`、`__linux`、
  `__OHOS__`），不会落到 `#error "s.h: add your platform here"`。
- 构建参数是唯一适配面。上游 makefile 会用**构建机**的 `uname` 推导
  `-D NAN_BOXING`，并按默认 `PREFIX=/usr/local` 编入
  `-DLIBDIR=/usr/local/share/skint/lib`；交叉编译时这两处都会按构建机
  取值。配方在 `make` 命令行整体覆盖 `CFLAGS`，把它们钉死。
- 产物只依赖 musl libc：`libm` 已并入 `libc.so`，`DT_NEEDED` 恰为
  `[libc.so]`（glibc aarch64 产物会多出 `libm.so.6`）。
- 上游的 `configure` 是个 8 行 bash 脚本（只写 `prefix.mk`），配方不调用它，
  顺带避开 E165（OHOS 无 `/bin/bash`）。
- `%system` 走 musl 的 `system()` → `/bin/sh`；这是上游 SRFI 汇总入口
  `test/srfi/all.scm` 逐个跑子模块所依赖的能力，真机上由 test_package 的
  H1 用例单独验证。

## 依赖

- 构建/运行：无第三方依赖（仅 C 运行时）。
- 测试：上游自带两套测试，由本包 `build()` 在真机上真实执行。

## 参考资料

- 上游仓库：<https://github.com/false-schemers/skint>
- R7RS-small 报告：<https://small.r7rs.org/>
