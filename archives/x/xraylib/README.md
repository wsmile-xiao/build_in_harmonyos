# xraylib

X-ray matter interaction cross sections library for X-ray fluorescence (XRF) applications. ANSI C core (`libxrl`) with 50+ functions for photoelectric/Compton/Rayleigh cross sections, line/edge energies, fluorescence yields, scattering factors, refractive indices and more.

## OHOS 适配

- Autotools 构建：`autoreconf` 自举后 `./configure --disable-all-bindings && make && make check && make install`。
- 仅构建核心 C 库 `libxrl`（关闭 Fortran/Python/Perl/Java/Lua/Ruby/PHP/Pascal/IDL 全部绑定，无额外依赖，仅需系统 `libm`）。
- 上游 `tests/` 含 27 个 C 测试程序，配方 `build()` 中全量 `make check` 运行。
- 公开头安装于 `include/xraylib/`（`#include <xraylib.h>` 需 `-I.../include/xraylib`，配方已声明双 include 目录兼容两种写法）。

## 依赖

- 构建：`automake/1.18`、`autoconf/2.72`、`libtool/2.5.4`（GitHub archive 无 `configure`，需自举）。
- 运行：系统 `libm`（`find_library m`）。

## 参考

- 上游仓库：https://github.com/tschoonj/xraylib
- 文档 Wiki：https://github.com/tschoonj/xraylib/wiki
