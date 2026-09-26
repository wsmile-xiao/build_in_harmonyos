# lbt 1.2.2 适配笔记

## 编译环境
- 构建系统: makefile（手写 Makefile，无 configure）
- 编译日期: 2026-09-23
- 编译器: clang++ / clang 15（OHOS SDK 26.0.0.18）
- 状态: built

## 编译步骤

1. 取 Debian pool 的 `lbt_1.2.2.orig.tar.gz`（HTTPS，sha256 已固定）。
2. `make CXX=clang++ CC=clang CXXFLAGS="-std=gnu++98 -O2 -fno-exceptions -fno-rtti -Wall" CFLAGS="-O2 -Wall" -j1`，产出 `lbt` 与 `lbt2dot`。
3. `package()` 安装两个可执行文件、man 手册与 `doc/` HTML 文档。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++17 下无法编译 | `BitVector.h` 使用 `register` 存储类，C++17 已移除 | 以 `-std=gnu++98` 编译（源码为 2001 年的 C++98 代码），零补丁 |
| 2 | 源码只在明文 HTTP 发布 | 上游 `http://www.tcs.hut.fi/...`，仓库规则禁止 conandata 明文 `http://` | 用 Debian 同版本 `.orig.tar.gz`（HTTPS）并固定 sha256 |
| 3 | 命令行 CXXFLAGS 覆盖 Makefile 默认 | `CXXFLAGS+=...` 在命令行变量存在时不生效 | 在传入的 CXXFLAGS 中显式带上 `-fno-exceptions -fno-rtti -O2` |

## 依赖版本

无三方依赖。

## 验证结果

```bash
# 上游测试：无（N=0）
# 消费者（test_package/test_lbt.sh）
LBT_CHECK_SUMMARY checks=13 fails=0
# 其中：printf 'G p0' | lbt | lbt2dot 产出 GraphViz digraph
```

## 注意事项

- `lbt`/`lbt2dot` 是过滤器（stdin → stdout）；消费者测试用 `G p0` 公式验证翻译与 GraphViz 转换。
