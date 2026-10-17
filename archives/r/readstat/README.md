# readstat

ReadStat 是一个 MIT 许可的 C 语言库与命令行工具集，用于**读取（并写入）**三大统计软件的数据文件：SPSS（`.sav` / `.zsav` / `.por`）、SAS（`.sas7bdat` / `.sas7bcat` / `.xpt`）与 Stata（`.dta`）。上游由 Wizard（WizardMac）开发，是 haven、ReadStat CLI 等工具的底层解析引擎。

## 功能概述

- **读取**：SPSS SAV/ZSAV/POR、SAS7BDAT/SAS7BCAT/XPORT、Stata DTA（104–119 全版本），带行偏移/行上限、进度回调与自定义 IO 回调。
- **写入**：SAV（含行压缩与 ZSAV zlib 二进制压缩）、DTA、XPORT、CSV/JSON 元数据导出。
- **命令行工具**：`readstat`（格式转换，`--version`/`--help` 可用）与 `extract_metadata`（导出 JSON 元数据）。
- **编码转换**：通过 `iconv` 处理 Windows-1252、UTF-8、EUC-JP 等字符集。

## 依赖关系

- 运行/编译依赖：`zlib`（可选特性 ZSAV 的读写；本仓库配方显式声明，避免静默链接 SDK 系统 libz）、`iconv`（HarmonyOS libc 内置，无需额外包）、`-lm`。
- 可选（本配方关闭，上游测试面不覆盖）：`libxlsxwriter`（写 xlsx，制品仓无此包）、`libcsv`（读裸 CSV）。
- 构建期工具（`tool_requires`）：`automake/1.18`、`libtool/2.5.4`、`gettext/0.22.5.1`——GitHub tag 归档不含预生成的 `configure`，须 `autoreconf -fi`，而 `configure.ac` 同时使用 `LT_INIT` 与 gettext 的 `AM_ICONV` 宏。

## OHOS 适配要点

1. **config.guess 不认识 HarmonyOS**：`uname` 返回 `HarmonyOS`，须显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（同时命中 configure.ac 的 `*linux*` 分支取得 `-lm`）。
2. **HMDFS 临时目录族**：生成的 `configure` 以 `umask 077` + `mktemp -d "./confXXXXXX"` 建 scratch 目录，在 HMDFS 上落成 2700 目录导致 `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied`；构建期归一为 `umask 022` / `${TMPDIR:-.}`（E011 同族标准修法，不产生补丁文件）。
3. **clang 15 + 上游 `-Werror`**：`-Wstrict-prototypes` 在 clang 15 默认开启，上游 `foo()` 形参空表声明（如 `print_version()`、`machine_is_little_endian()`）会以 `-Werror` 直接失败；以 `CFLAGS` 追加 `-Wno-strict-prototypes` 关闭该告警（不改上游源码）。
4. **上游测试必须带 zlib**：`make check` 的用例集会写读 ZSAV（`RT_FORMAT_SAV_COMP_ZLIB` 属于 `RT_FORMAT_SPSS`），关闭 HAVE_ZLIB 会真实失败。
5. 无 `ragel` 时安全：9 个 `.rl` 文法的生成产物 `.c` 已随源码签入，且 `Makefile.am` 只把 `.c` 列为源，`RAGEL=true`（未安装时的回退值）不会破坏构建。

## 参考资料

- 上游仓库：https://github.com/WizardMac/ReadStat
- 上游 CI（`autoreconf -i -f && ./configure && make && make check`）：`.github/workflows/build.yml`
- 版本级编译记录见 `1.1.9/notes.md`，构建元数据见 `1.1.9/manifest.yaml`。
