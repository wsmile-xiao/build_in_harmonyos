# zst

## 简介
`zst` 是一个**单文件命令行压缩前端**：把四个「必备压缩库」——zstd、xz(LZMA2)、gzip(zlib)、bzip2——统一到一个小二进制里，
按参数 / 文件后缀 / `argv[0]` 自动分派算法。作者设计目标是替代各自冗长的官方 CLI（体积小、行为一致、压缩级别统一 1–9）。

上游定位（README 原文）：`zstd` 快但 CLI 体积大（>2MB）、不删源文件、级别刻度与世界不一致；而 `libzstd`/`zlib`/`libbz2`/`liblzma`
本已是「必备」库，索性由一个二进制统一提供四种压缩格式。

## 产物
- `bin/zst`（单个静态自包含可执行文件，`DT_NEEDED` 仅 `libc.so`）
- `share/man/man1/zst.1`
- 按 `argv[0]` 分派：`zst` / `unzst` / `zstcat`（以及软链成 `gzip`/`gunzip`/`bzcat`/`xzcat`/`zstdcat` 等时的兼容行为）

## OHOS 适配
- cmake 构建；上游 `cmake_minimum_required(2.8.12)` 被 cmake 4.x 拒绝 → `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
- 上游用 `CHECK_LIBRARY_EXISTS` + `-l<name>` 找压缩库，不做 `find_package`：
  显式传依赖 `-I`，并把**只含 `.a` 的私有 lib 目录**挂到 `CMAKE_REQUIRED_LINK_OPTIONS` + `CMAKE_EXE_LINKER_FLAGS`，实现四库静态链接
- 自发现 `ohos.toolchain.cmake` + 裸 cmake（不经 conan_toolchain，ML-0035）
- 二进制经 `binary-sign-tool -selfSign` 重新签名（HarmonyOS PC XPM）

## 依赖
- `zlib/1.3.1`、`bzip2/1.0.8.2`、`xz/5.6.2`（提供 liblzma）、`zstd/1.5.7.1`（需其 `libzstd.a`）
- 均为 ohpcd 已发布制品；全部静态链入 `bin/zst`

## 功能验证
```bash
echo "test" | zst -Fzstd > out.zst && zst -d out.zst      # zstd 往返
zst -Fxz file && zst -d file.xz                            # xz 往返
zst -Fgzip file && zst -d file.gz                          # gzip 往返
zst -Fbzip2 file && zst -d file.bz2                        # bzip2 往返
```

## 版本
- 0.4: built (2026-09-23)，cmake 配方，静态自包含 `bin/zst`

## 参考
- 上游: https://github.com/kilobyte/zst
