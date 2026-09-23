# ncompress — OpenHarmony 编译档案

## 软件简介
ncompress（Ncompress）是经典 Unix `compress` 工具的现代维护分支（vapier 维护），
基于 LZW 的快速简单文件压缩器，输出 `.Z` 格式。提供 `compress` / `uncompress` / `zcat`
命令以及 `zcmp`/`zdiff`/`zmore` 辅助脚本。许可证为 Unlicense（公有领域）。

## OHOS 适配要点
- 单文件 C 工具（`compress.c`），无 configure/autotools、无编译期依赖，直接 clang 编译
- 编译选项沿用上游：`-DUSERMEM=800000 -DUTIME_H -DLSTAT`（默认无 `-DBYTEORDER`，
  走可移植位流路径，aarch64 无需端序特殊处理）
- `uncompress`/`zcat` 按 `argv[0]` 区分模式：打包为同名副本即可（上游用硬链接，等价）
- 上游测试 `make check` → `tests/runtests.sh`，在 build() 中以 CONFIG_SHELL/bash 运行

## 依赖关系
- 无编译/运行依赖（仅 C 运行时）
- 被依赖: 无（独立 CLI 工具）

## 参考资料
- [vapier/ncompress (GitHub)](https://github.com/vapier/ncompress)
- [ncompress release v5.0](https://github.com/vapier/ncompress/releases/tag/v5.0)
