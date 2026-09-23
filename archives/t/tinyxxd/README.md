# tinyxxd

> 小型、自包含的 `xxd` 克隆：把文件转成十六进制/二进制转储，也能从转储还原。

## 简介

tinyxxd 用单个 C11 源文件实现，是 ViM 自带 `xxd` 的精简替代品，不依赖任何外部库。
它支持多种输出风格（十六进制、二进制位、little-endian、C include、PostScript 纯十六进制）、
`-r` 反向还原、`-s` 定位、`-c` 每行字节数、`-g` 分组、`-R` 着色等。

## OHOS 适配要点

- 单个 C11 源文件，直接编译：`clang -std=c11 -D_GNU_SOURCE -O2 main.c -o tinyxxd`。
- 安装 `bin/tinyxxd` 与 `share/man/man1/tinyxxd.1`。
- 上游 `make test` 会下载 ViM 的 `xxd` 作对照、并构建 ASan 版本，不适合干净 CI；
  本包改为复现 `testfiles/` 下的自包含用例与 `make test` 中不依赖 xxd 的用例。
- 产物是命令行工具，软件级提供 `commands.json`（R38）。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| （无） | - | 仅 C 标准库 |

## 功能验证

```bash
printf 'hello world' > sample.bin
tinyxxd -c 0 -ps sample.bin        # -> 68656c6c6f20776f726c64
tinyxxd sample.bin > dump.hex
tinyxxd -r dump.hex > restored.bin # restored.bin 与 sample.bin 相同
```

## 参考

- [源码仓库](https://github.com/xyproto/tinyxxd)
- [上游 README](https://github.com/xyproto/tinyxxd/blob/main/README.md)
