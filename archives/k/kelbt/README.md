# kelbt

## 简介
kelbt 是 Adrian Thurston 编写的 Backtracking LR 解析器生成器，读取 `.kl` /
`.kh` 语法文件生成 C++ 回溯解析器，是 ragel/colm 家族的一员。源码自带 AAPL
容器库（纯头文件，LGPL-2.1）。

## OHOS 适配
- autotools 构建系统
- 上游发布包自带生成的 `klscan.cpp` / `klparse.{h,cpp}`（DIST 文件
  `build_parsers=no`），configure 无需 ragel/kelbt bootstrap
- `configure.ac` 未调用 `AC_CANONICAL_HOST`，无 config.guess 平台识别问题
- 终端工具静态链接（R26）
- 当前状态：本机前置完成（built），真机 shadow CI 待执行

## 依赖
- 编译工具：clang++、make、autotools
- 无外部运行时依赖

## 功能验证
```bash
kelbt --version    # Kelbt version 0.16 February 2015
kelbt -o out.h grammar.kh   # 从 .kh 语法文件生成 parser header
```

## 参考
- 官网: http://www.colm.net/open-source/kelbt/
- 源码: http://www.colm.net/files/kelbt/kelbt-0.16.tar.gz
