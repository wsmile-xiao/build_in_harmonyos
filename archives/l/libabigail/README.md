# libabigail

**libabigail** 是 Red Hat 开发的 ABI Generic Analysis and Instrumentation Library（C++ 库，Autotools 构建）。
它解析 ELF 二进制的 DWARF 调试信息，生成 ABI 表示，并可比较两个版本的 ABI 差异，输出报告。

## 功能概述

- `libabigail.so` — 核心 C++ 库（`abigail::ir` / `abigail::comparison` / `abigail::reader` 等命名空间）
- `abidw` — 把 ELF/DWARF 转成 ABI XML
- `abidiff` — 比较两个二进制/ABI XML 的差异
- `abilint` — 校验 ABI XML
- `abicompat` — 检查库与二进制的 ABI 向后兼容
- `abipkgdiff` — 比较软件包（RPM/DEB/tar）的 ABI
- `kmidiff` — 比较 Linux 内核模块 ABI

## OHOS 适配

- **平台检测**：config.guess/config.sub 打补丁识别 `aarch64-unknown-linux-ohos`（E007），禁止 `--build/--host` 绕过
- **HMDFS 临时目录**：configure umask 077→022（E129）；temp_file 优先使用 `$TMPDIR`（E002）
- **libc++ 兼容**：`tr1/*` → `std/*` 现代化；`__gnu_cxx::stdio_filebuf` → `std::fstream`；
  `get_current_dir_name()` → `getcwd()`；shared_ptr→bool 显式转换
- **依赖**：libxml2（XML 解析）、elfutils（libelf/libdw）、musl-fts（fts.h/libfts）

## 依赖关系

- 编译/运行依赖：`libxml2/2.15.3`、`elfutils/0.195`、`musl-fts/1.2.7`
- 传递依赖（elfutils）：zstd、bzip2、xz、argp-standalone、musl-obstack

## 参考资料

- 官网: https://sourceware.org/libabigail/
- 源码: https://sourceware.org/pub/libabigail/libabigail-1.4.tar.gz
