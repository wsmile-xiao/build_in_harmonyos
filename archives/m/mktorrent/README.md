# mktorrent

> 创建 BitTorrent metainfo (.torrent) 文件的命令行工具

## 简介

mktorrent 用于从单个文件或整个目录生成 BitTorrent 协议所需的 metainfo（.torrent）文件。
默认构建使用内置 SHA1 实现、单线程哈希，仅依赖 libc，不引入 OpenSSL / pthread。

上游：https://github.com/Rudde/mktorrent ，许可证 GPL-2.0-or-later。

## OHOS 适配要点

- 纯 GNU Make 项目（GNUmakefile + Makefile + rules.mk），无 configure 脚本，直接 `make` 构建。
- 构建命令传入 `OFFPRFX=l`：上游 Makefile 会构建并运行一个 `prefix` 辅助程序来探测 off_t 的 printf 宽度，而 OHOS 上未签名的新构建 ELF 无法在构建期执行；aarch64 下 `off_t == long`（8 字节），正确宽度即为 `l`，故直接给出、跳过运行。
- 启用 `USE_LONG_OPTIONS=1`，获得 `--help`/`--announce` 等长选项（getopt_long，musl 提供）。
- HarmonyOS 无 `install(1)`，package 阶段用 `copy()` 直接安装 `mktorrent` 二进制。
- OHOS 执行二进制需 ELF 签名，package 阶段用 `binary-sign-tool` 自签名。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| musl libc | 系统自带 | 文件/目录操作；SHA1 为内置实现 |

## 功能验证

```bash
printf 'hello\n' > input.txt
mktorrent -a http://example.com/announce -o out.torrent input.txt
```

## 参考

- [上游仓库](https://github.com/Rudde/mktorrent)
