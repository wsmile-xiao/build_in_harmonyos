# mrcal

`mrcal` 是相机标定与几何库（C 核心 + C++ + Python 绑定）。

## 适配要点

- 上游用自研 **mrbuild** 构建框架（不在 tarball 内）。配方在 `source()` 里另取
  `codeload.github.com/dkogan/mrbuild` 的 `v1.16`（sha256 校验）解到 `mrbuild/`。
- 两个生成文件需在构建期生成：`cameramodel-parser_GENERATED.c`（**re2c**，
  `tool_requires`）与 `minimath/minimath_generated.h`（perl）。
- 依赖：`libdogleg`、`suitesparse`(CHOLMOD)、LAPACK/BLAS（由 `lapack/3.12.1`
  → `openblas` 提供）、`libpng`、`libjpeg-turbo`、`stb_image`（头文件）。
- 补丁 4 个：
  1. 去掉 `python-cameramodel-converter.c`（需 CPython+numpy 头，仅 Python 绑定用）；
  2. `minimath_generate.pl` 去掉 `List::MoreUtils`（build-only CPAN），改可移植循环；
  3. mrbuild 的 `-Wl,--default-symver`（GNU ld 专有，lld 不支持）注释掉；
  4. `test-parser-cameramodel.c` 的硬编码 `/tmp` 改相对路径（OHOS 不可写 `/tmp`）。
- Conan 的 `stb_image` 只装 `include/stb_image.h` 而 mrcal 用 `<stb/stb_image.h>`，
  配方建 `stb/` shim 目录并加入头路径。

## 上游测试

`test.sh` 列出 62 个测试条目（40 个 `test-*.py` + 5 个 C 程序等）。配方构建并实跑
其中**不需要 Python 的 4 个纯 C 程序**：`test-cahvor`、`test-heap`、
`test-lensmodel-string-manipulation`（30 项）、`test-parser-cameramodel`（122 项）。
其余 Python 套件需 CPython+numpy+scipy 与 `_mrcal` 扩展，本环境不具备（见 MANIFEST）。

## 消费者测试

`test_package/test_mrcal.c`：链接安装后的 `libmrcal.so`，验证
`mrcal_lensmodel_num_params`/`name`/`type_from_name`（9 项断言）。

## 产物

| 路径 | 说明 |
|---|---|
| `lib/libmrcal.so`（及 `.so.5`/`.so.5.0`） | 核心库 |
| `include/mrcal.h` 等 12 个头 | 公共头 |
