# unalz

> 从 ALZ（AlZip）归档中列出/解压文件的命令行工具

## 简介

unalz 是韩国 AlZip 归档格式（ALZ）的解压工具，由 kippler 开发（2004–2009，
zlib 许可证）。支持列出归档内容、按名选择性解压、管道解压，以及 EUC-KR/CP949
文件名到 UTF-8 的转换（OHOS musl libc 内置 iconv 支持 CP949 别名）。

源码内捆绑 zlib 与 bzip2 解压子集，无外部依赖。

## 输出

| 产物 | 类型 | 说明 |
|------|------|------|
| `unalz` | CLI | 主命令行工具（列出/解压 .alz 文件） |

## 用法

```bash
unalz [<switches>...] archive.alz [<file names to extract>...]
```

| 选项 | 说明 |
|------|------|
| `-utf8` / `-cp949` / `-euc-kr` | 文件名码页转换目标（默认按源码内码表处理） |
| `-l` | 列出归档内容 |
| `-d directory` | 设置解压输出目录 |
| `-p` | 管道模式：文件内容写 stdout，无进度消息 |
| `-pwd <pwd>` | 设置解压密码 |
| `-v` / `--version` | 输出版本信息（适配补丁添加） |
| `-h` / `--help` | 输出帮助信息（适配补丁添加） |

示例：

```bash
unalz -l sample.alz          # 列表
unalz -d out sample.alz      # 解压到 out/
unalz -utf8 -d out kr.alz    # EUC-KR 文件名转 UTF-8 解压
```

## OHOS 适配要点

- 上游 Makefile 硬编码 `CC=gcc`/`CPP=g++`，配方以 make 命令行变量注入 clang/clang++。
- make 目标选 `linux-utf8`（`-D_UNALZ_ICONV -D_UNALZ_UTF8`）：musl 内置 iconv，
  无需 `-liconv`。
- 移植补丁：`get_crc_table()` 返回值强转（OHOS SDK zlib 头为 `z_crc_t*` 原型）与
  `-v/--version`、`-h/--help` 开关（过标准版本探针）。
- 上游错误路径恒 `return 0`（缺失/损坏归档只打印错误文本）——自动化断言须打输出文本。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.65 | built | 首次适配 |
