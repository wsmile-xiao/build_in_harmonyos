# makefile2graph v1.5.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: `curl -L -o makefile2graph-v1.5.0.tar.gz https://github.com/lindenb/makefile2graph/archive/refs/tags/v1.5.0.tar.gz`
2. 解压源码
3. 直接编译: `make CC=clang -j1` (无 configure 步骤)
4. 安装到 staging: `make install DESTDIR=<prefix>`

## 遇到的问题与解决方案

无问题。makefile2graph 是纯 C 程序，仅依赖标准 C 库 (stdio, stdlib, string, ctype, unistd, errno, getopt)，编译一次通过。

## 源码修改

无补丁，源码无需修改即可在 HarmonyOS 上编译。

## 依赖版本

无外部依赖。

## 验证结果

```bash
$ ./make2graph --version
1.5.0

$ make -Bnd 2>/dev/null | ./make2graph --format l
<ROOT>
all
make2graph
make2graph.c

$ make -Bnd 2>/dev/null | ./make2graph --format x
<?xml version="1.0" encoding="UTF-8"?>
<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">
  <meta>
    <creator>https://github.com/lindenb/makefile2graph version:1.5.0</creator>
    <description>Creates a graph from a Makefile</description>
```

## 交付物

| 文件 | 说明 |
|------|------|
| make2graph | C 二进制程序，解析 make -Bnd 输出 |
| makefile2graph | shell 脚本，封装 make -nd | make2graph |

## 注意事项

- make2graph 的 `--format d` (DOT 格式) 需要 graphviz 的 `dot` 命令才能渲染图形，但 make2graph 本身不依赖 graphviz
- `make check` 中的第一个测试需要 `dot`，其他测试不需要
---

**编译结束**: 2026-07-15 16:41
**最终状态**: built
