# ucon64

> uCON64 — the Universal Console file and backup tool, 用于管理和备份各种游戏机 ROM 和备份单元

## 简介

uCON64 是一个命令行工具，用于管理和操作各种游戏机的 ROM 镜像和备份单元。它支持多种游戏机平台（包括 NES、SNES、Genesis/MegaDrive、N64、GBA 等），提供 ROM 头部信息识别、CRC/SHA1/MD5 校验、ROM 格式转换、备份单元管理等功能。

uCON64 使用 C 语言编写，基于 autotools 构建系统，无需外部依赖（内嵌 zlib）。它是一个独立的终端工具，适合静态编译。

## OHOS 适配要点

1. **config.guess/config.sub**: 源码包使用 2017 版 config.guess/config.sub，不识别 HarmonyOS 平台，需原地修补添加 HarmonyOS 检测分支
2. **umask 权限**: configure 中 umask 077 在 HMDFS 上创建的目录无法写入，需改为 022
3. **并口支持**: aarch64 无 I/O 端口访问（inb/outb），必须使用 --disable-parallel
4. **静态链接**: 终端工具必须静态链接（R26），LDFLAGS=-static
5. **in-tree 构建**: ucon64 不支持 out-of-tree 构建，conanfile.py build() 必须在 source_folder 中运行
6. **make -j1**: HMDFS 不支持 mkfifo，必须使用 -j1 避免 make jobserver 问题

## 排除与替代

无。ucon64 功能独立，无需要排除的组件。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | - | ucon64 无外部依赖，zlib 已内嵌 |

## 功能验证

```bash
ucon64 --version    # 输出版本信息
ucon64 --help       # 输出帮助信息
ucon64 --crc ROM.bin  # 计算 ROM 的 CRC32
```

## 参考

- [官方网站](https://ucon64.sourceforge.net/)
- [SourceForge 项目](https://sourceforge.net/projects/ucon64/)
