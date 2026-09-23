# xlslib

`xlslib` is a multiplatform C/C++ library for dynamically generating
Microsoft Excel(TM) `.xls` (BIFF8) files directly from code, without needing
Excel to be installed.

## 功能概述

- Create multi-sheet workbooks with the C++ (`workbook` / `worksheet`) or C
  (`xlsNewWorkbook` / `xlsWorkbookSheet`) interfaces.
- Add label, number, blank, formula and merged cells with rich formatting
  (fonts, colors, borders, number formats, row heights, column widths).
- Dump the workbook to a real `.xls` file with `wb.Dump("file.xls")`.
- Ships a C++ test suite (`targets/test`) that validates generated files
  against MD5 reference hashes.

## OHOS 适配

- Built static-only with Autotools. The bundled libtool 2.2.10 creates
  `#!/bin/bash` wrapper scripts for shared-library check programs, and OHOS
  has no `/bin/bash`; `--disable-shared` avoids this entirely.
- The bundled 2009 `config.sub` does not know aarch64, so it is patched to
  accept `aarch64-*-linux*` / `aarch64-*-ohos*`. On OHOS the configure step
  pins `--build=--host=aarch64-unknown-linux-gnu` (native, build == host).
- The upstream check programs linked with `-static -lstdc++`, which fails on
  OHOS (no static libc, libc++ runtime). The test Makefile drops those flags
  and links the C `testC` driver through the C++ compiler driver.
- The shipped generated Autotools files are older than their `.ac`/`.am`
  sources; they are touched after extraction so `autoconf`/`automake` are
  never invoked.

## 依赖关系

- No third-party library dependencies. Requires a C++ toolchain (clang on
  OHOS) and standard POSIX headers.

## 参考资料

- 官网: https://sourceforge.net/projects/xlslib/
- 源码仓库: https://github.com/JanX2/xlslib
- 版本: 2.5.0 (xlslib-package-2.5.0.zip)
