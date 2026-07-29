# flex

## 简介
flex (Fast Lexical Analyzer Generator) 是一个快速词法分析器生成器，用于生成扫描器（tokenizer）来匹配文本中的模式。常与 bison/yacc 配合使用。

## OHOS 适配
- 使用 autotools 构建系统
- 通过 `--build=aarch64-unknown-linux-gnu` 绕过 config.guess 无法识别 OHOS 的问题
- 补丁 0006: configure mktemp 模板改用 `${TMPDIR:-/tmp}` 避免 HMDFS 权限问题
- 静态链接（R26 规则）
- 当前编译状态：已完成（built）

## 依赖
- 编译工具: clang, make, autotools
- bison（可选，用于 flex 自身构建）

## 功能验证
```bash
flex --version    # flex 2.6.4
```

## 参考
- GitHub: https://github.com/westes/flex
- 源码: https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz
