# cldump

> Clarion database files extractor: dumps Clarion (.dat) databases to text, SQL and CSV.

## 简介

cldump extracts the data contained in a Clarion database. Clarion is a Windows
IDE similar to Delphi, with its own simple database format. cldump can export
the content to CSV or SQL (including schema, keys and indexes), plus its own
human-friendly format with full meta data.

Upstream 0.11 is a small plain-Makefile C program (single `cldump` binary, no
library, no dependencies beyond libc). Debian `0.11~dfsg` repacks the same
upstream tarball without non-free docs; the Conan version `0.11-dfsg` maps
Debian's `~dfsg` suffix to a Conan-safe `-dfsg` suffix.

## OHOS 适配要点

- 上游是手写 Makefile（`src/Makefile`，无 configure、无 install、无 check
  目标）：`build()` 直接在 `src/` 子目录运行 `make -j1`，产物为单一可执行
  文件 `cldump`，手动安装到 `<pkg>/bin`。
- Makefile 默认 `CFLAGS = ...` 会覆盖 Conan 注入的编译旗标，已用补丁改为
  `CFLAGS += ...` 并在链接行追加 `$(LDFLAGS)`（Debian 01-hardening.patch
  同法），保证 Conan buildenv 的 flags 生效。
- 编译器经 `tools.build:compiler_executables` 从 Conan 配置获取后以
  `make CC=...` 显式传入（R33：不在 `self.run` 里裸用 `$CC`）。
- 上游无任何自动化测试（见 `test_package/MANIFEST.yml` 审计）：`build()`
  不调用 `make check`；改为构建后冒烟验证（`--version` 退出 0），
  test_package 对安装后的二进制做 4 项真实执行断言。

## 依赖

无（仅 libc：stdio/stdlib/string/mmap/iconv 均在系统 libc 内解析）。

## 功能验证

```bash
cldump --version   # 期望输出: cldump v0.11 - Clarion database extractor
cldump --help      # 期望输出: Usage: ...
```

## 参考

- 上游作者站（历史）: http://www.technologeek.org/projects/cldump/
- Debian 源码包: https://salsa.debian.org/debian/cldump
- Debian 源码池: https://deb.debian.org/debian/pool/main/c/cldump/
