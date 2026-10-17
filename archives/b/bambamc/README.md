# bambamc

bambamc（[gt1/bambamc](https://github.com/gt1/bambamc)，German Tischler /
Genome Research Limited）是一个轻量的 C 语言库，实现**按名称归并的 BAM 文件读入与写出**：
把 BAM/SAM 比对记录解码为可比较的条目、按 query name 归并配对，再以 BAM/BGZF 格式输出。

## 功能概述

- BAM/SAM 解码：`BamBam_BamFileDecoder`、`BamBam_SamFileDecoder`、`BamBam_SamBamFileDecoder`
- BAM 写出：`BamBam_BamWriter` + `BamBam_BamHeaderInfo`（含 `PutAuxNumber` 辅助标签）
- BGZF/gzip 层：`BamBam_BgzfCompressor`、`BamBam_GzipReader`、`BamBam_GzipWriter`（基于 zlib）
- 按名称归并：`BamBam_BamCollator` 及其哈希/向量/临时文件后端
- 格式化输出：`BamBam_PutAlignmentFastQBuffer`（比对还原为 FASTQ，自动处理反向链反向互补）
- 单条比对访问器：`BamBam_BamSingleAlignment_*`（refID/pos/flags/MQ/TLen/LSeq/read name/cigar/seq/qual）

## OHOS 适配要点

1. **自举顺序**：官方 tag 压缩包不含生成的 `configure`。配方顺序固定为
   「放 `m4/pkg.m4` → `autoreconf --force --install` → 打 `config.guess`/`config.sub` 补丁 →
   归一化 `umask 077` → `configure` / `make`」。补丁若在 `autoreconf` 之前应用会被覆盖。
2. **pkg.m4**：`configure.in` 使用 `PKG_PROG_PKG_CONFIG`/`PKG_CHECK_MODULES`，而 `pkg.m4`
   不在 aclocal 的隐式搜索路径，宏不展开会让 `configure` 直接报 shell 语法错误；
   配方随包携带 `m4-pkg.m4` 并在 autoreconf 前放入源码树 `m4/`。
3. **config.guess/config.sub**：autoreconf 现场生成的是 autoconf 2.73 自带的 2024-07-27 版，
   不识别 `uname -s` = `HarmonyOS`；两个补丁补回 `aarch64-unknown-linux-ohos` 识别与
   `ohos-linux` 三元组合法性。**未**使用 `--build`/`--host` 绕过（native 编译）。
4. **HMDFS 权限**：autoconf 的 `config.status` 模板用 `umask 077 && mktemp -d`，在 HMDFS 上
   生成的临时目录对创建者自身不可写，`configure` 报
   `can't create ./confXXXXXX/subs1.awk: Permission denied`；配方把生成的 `configure`
   归一化为 `umask 022`。
5. **zlib 变体选择**：本包默认静态（`shared=False`）。静态库要被下游共享对象吸收，依赖必须是
   **PIC** 变体。本仓的 `zlib/1.3.1`、`zlib/1.3.1.1`、`zlib/1.3.2` 在 OHOS profile 下解析出
   **同一个 `package_id`**（`6b129b06…`），但只有后两者在配方里注入了 `CFLAGS="-fPIC -O2"`；
   选中 `zlib/1.3.1` 会在链接期报
   `R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'`。本包钉 `zlib/1.3.1.1`。
6. **断言不被编译掉**：上游测试程序是 `assert` 自检式（`--enable-fast` 默认 `no`），而 Conan
   Release profile 会给 `AutotoolsToolchain` 注入 `-DNDEBUG`；配方置 `tc.ndebug = None`
   使断言保持启用，测试才是真实执行。

## 依赖关系

- 编译/运行：`zlib/1.3.1.1`（OHOS armv8 静态 PIC `libz.a`）
- 构建工具（tool_requires）：`automake/1.18`、`libtool/2.5.4`（干净构建环境无系统 automake/libtool）

## 已知限制

- 只验证 `os=OHOS`/`Linux` 且 `arch=armv8`；其他平台组合由 `validate()` 拒绝。
- 包内只有静态库 `lib/libbambamc.a`（无 `bin/`、无共享库），因此软件级不提供 `commands.json`。
- 上游 `make check` 是空套件（无 `TESTS` 注册）；真实测试入口是 `bamreadertest`/`bamwritertest`
  两个程序，由配方在 `build()` 内显式运行。`bamreadertest.c` 中的 `lineBufferTest()` /
  `samBamSamTest()` 在 `main()` 中被上游注释掉，不构成 PASS 或 SKIP。

## 参考资料

- 上游仓库：https://github.com/gt1/bambamc
- 版本级细节与实测证据：`0.0.50/notes.md`、`0.0.50/reports/conan-verify-supplement.md`
