# CTPL (C Template Parser Library)

> C 语言编写的模板解析引擎库，可从内存/本地/远端流式解析模板并精细控制解析环境。

## 简介

CTPL（C Template Parser Library）是由 Colomban Wendling 维护的 C 模板引擎，
核心为 `libctpl`（环境/词法/求值/解析/输入输出流/令牌/值对象）与可选的 `ctpl`
命令行工具。模板语法支持变量替换、表达式、数组、数学函数与国际化，文档见
`docs/reference`（gtk-doc）。

0.3.5 为 0.3 分支的 bugfix/enhancement 合集（含 `ctpl_value_take_string` 减拷贝、
GCC 14 构建修复）。

## OHOS 适配要点

- 使用官方 release tarball（含预生成 configure/Makefile.in），避免 GitHub tag 包
  的 autoreconf 链依赖（真机缺 automake/libtool）。
- `config.guess` 无法识别 HarmonyOS：固定
  `--build/--host=aarch64-unknown-linux-gnu` 绕过探测，编译器仍经 Conan 工具链
  指向 OHOS sysroot/target（cdecl/castget 先例）。
- 硬依赖 `glib-2.0 >= 2.10`、`gio-2.0`（CLI 另需 `gio-unix-2.0`）：配方
  `requires glib/2.88.0` + `PkgConfigDeps` + `tool_requires pkgconf/3.0.5` 满足。
- glib 传递依赖的 plain `zlib/1.3.1` 在 OHOS 会误走官方 CMake 配方，需
  `zlib/1.3.1.1` override 锁定 OHOS 专用版本（cassbeam 先例）。
- HMDFS 约束：configure 内 `umask 077 -> 022` 宽松，预置 `PWD` 与可写
  `TMPDIR/TMP/TEMP`（真机 /tmp 只读）。
- 头文件安装于 `include/ctpl/*.h`，经 `<ctpl/ctpl.h>` 统一入口消费；
  `CtplValue` 类型枚举为 `CTPL_VTYPE_*`，以 `ctpl_value_get_held_type()` 判型。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.88.0 | glib-2.0/gio-2.0/gio-unix-2.0（模板引擎运行时） |
| zlib | 1.3.1.1 | override：glib 传递依赖的 OHOS 专用版本 |
| pkgconf | 3.0.5 | tool_requires：提供 pkg-config 供 PKG_CHECK_MODULES |
| libm | 系统 | `AC_CHECK_LIB([m], [acos])` 数学函数 |

## 功能验证

```bash
# 消费者测试：模板替换 + environ API + 错误路径（3 用例）
ctest --output-on-failure
./test_ctpl
# 上游套件：testsuite 全集（parsing/float/number + CLI 复跑）
make check -j1
```

## 参考

- 官网: https://ctpl.tuxfamily.org/
- 源码仓库: https://github.com/b4n/ctpl
- 发版目录: https://download.tuxfamily.org/ctpl/releases/
