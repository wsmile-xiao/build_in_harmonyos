# corkscrew 2.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-04
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

```bash
CC=clang CXX=clang++ ./configure --prefix=$HOME/usr/local
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: no acceptable cc found | clang 不在 PATH | 设置 CC=clang CXX=clang++ |
| 2 | configure: can not guess host type | config.guess 不支持 HarmonyOS | 修改 config.guess |
| 3 | Invalid configuration aarch64-unknown-linux-ohos | config.sub 不支持 aarch64 | 修改 config.sub |

## 源码修改

- 0001-config.guess.patch: 添加 HarmonyOS 系统识别
- 0002-config.sub.patch: 添加 aarch64 和 linux-ohos 支持

## 验证结果

```bash
$ ~/usr/local/bin/corkscrew --version
corkscrew 2.0 (agroman@agroman.net)
```