# miniasm

> 基于 OLC 的长读段 de novo 组装工具：输入 PAF 重叠，输出 GFA 组装图。

## 简介

miniasm 是一个快速的长读段（PacBio / ONT）de novo 组装器。它接收所有读段之间的
自身比对（all-vs-all overlap，通常是 PAF 格式），输出 [GFA](https://github.com/pmelsted/GFA-spec)
格式的组装图。与主流组装器不同，miniasm 不做 consensus，直接把读段拼接成
unitig 序列，因此碱基错误率与原始读段相同。

典型用法：

```sh
minimap2 -x map-pb reads.fq reads.fq | gzip -1 > reads.paf.gz
miniasm -f reads.fq reads.paf.gz > reads.gfa
```

## OHOS 适配要点

- 纯 C，无外部依赖之外的编译期依赖：需要 **zlib**（由 Conan `zlib/1.3.1` 提供）、
  `libm`；`pthread` 在 OHOS bionic 下随 libc 提供，无需显式链接。
- 上游是 Makefile 工程；本仓库按源文件逐个编译并显式传入 zlib 的 include/lib。
- 产物是命令行工具，软件级提供 `commands.json`（R38）。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| zlib | 1.3.1 | 读取 gzip 压缩的 PAF |

## 功能验证

```sh
miniasm -V                       # -> 0.3-r179
miniasm reads.paf > reads.gfa    # 从重叠生成 GFA
miniasm -f reads.fa reads.paf    # 附带序列的 unitig
```

## 参考

- [源码仓库](https://github.com/lh3/miniasm)
- [上游 README](https://github.com/lh3/miniasm/blob/master/README.md)
- [PAF 格式说明](https://github.com/lh3/miniasm/blob/master/PAF.md)
