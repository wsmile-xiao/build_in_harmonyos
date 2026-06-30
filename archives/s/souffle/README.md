# Souffle

Datalog编译器和解释器。Souffle将Datalog程序翻译为高性能C++代码，或直接解释执行。

## 概述

- **语言**: C++（C++17标准）
- **构建系统**: cmake
- **License**: UPL-1.0（Universal Permissive License）
- **官网**: https://souffle-lang.github.io/
- **源码**: https://github.com/souffle-lang/souffle

## 功能说明

Souffle是一个声明式逻辑编程语言（Datalog）的编译器。核心功能包括：
- Datalog语法解析和编译
- 递归规则计算（传递闭包等）
- 否定查询
- 聚合操作（max, min, count, sum）
- 符号类型和数值类型
- 解释模式执行（直接运行Datalog程序）
- 编译模式执行（生成C++可执行文件）

## 已编译版本

| 版本 | 状态 | 日期 | 说明 |
|---------|--------|------|-------|
| 2.5 | published | 2026-06-15 | 最小化构建（可选功能已禁用） |

## 构建配置（v2.5）

2.5版本因平台可用性限制，以下cmake选项已禁用：

| 选项 | 值 | 说明 |
|------|------|------|
| SOUFFLE_USE_CURSES | OFF | provenance交互显示（ncursesw可用但cmake无法识别） |
| SOUFFLE_USE_ZLIB | OFF | 文件压缩（可选） |
| SOUFFLE_USE_SQLITE | OFF | sqlite存储IO（可选） |
| SOUFFLE_USE_OPENMP | OFF | 并行执行（可选） |
| SOUFFLE_USE_LIBFFI | OFF | 外函数接口（可选） |
| SOUFFLE_GIT | OFF | git版本嵌入（tarball构建） |
| SOUFFLE_ENABLE_TESTING | OFF | 测试套（手动功能验证替代） |

核心Datalog编译器和解释器功能完全可用。解释模式使用`--no-preprocessor`参数运行。

## 运行方式

```bash
# 解释模式（推荐，需加--no-preprocessor）
souffle --no-preprocessor your_program.dl

# 查看帮助
souffle -h

# 性能分析工具
souffleprof
```

## 限制

1. 本平台缺少mcpp/gcc预处理器，必须使用`--no-preprocessor`
2. 编译输出模式（-o）因libc++ ABI兼容性问题暂不可用
3. 版本号字段为空（因tarball构建无git历史）
