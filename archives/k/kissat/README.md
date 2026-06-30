# Kissat — 紊凑型增量SAT求解器

## 软件简介

Kissat 是一个紧凑的增量SAT求解器，由 Armin Biere 开发和维护。它是 CaDiCaL 求解器的精简版本，专注于高效求解命题逻辑可满足性问题（SAT）。Kissat 在 SAT Competition 中多次获奖，是业界公认的高性能 SAT 求解器之一。

- **主页**: https://github.com/arminbiere/kissat
- **作者**: Armin Biere（弗莱堡大学 / 林茨约翰·开普勒大学）
- **许可证**: MIT
- **分类**: 逻辑求解器 / SAT求解器

## 主要特性

- 紧凑高效的 C 语言实现
- 增量求解模式支持
- 证明生成（DRAT/DPR格式）
- 多种求解策略（CDCL、局部搜索、预处理等）
- 无外部依赖（bare metal solver，仅链接 libm）

## 已编译版本

| 版本 | 状态 | 编译日期 | 编译器 | 构建系统 |
|------|------|----------|--------|----------|
| 4.0.4 | ✅ published | 2026-06-15 | clang 15.0.4 | custom |

## 编译特点

- Kissat 使用自定义 configure 脚本（非标准 autotools），不支持 `--prefix` 和 `make install`
- 安装需手动复制二进制文件和库文件到目标目录
- 推荐配置参数: `./configure CC=clang`
