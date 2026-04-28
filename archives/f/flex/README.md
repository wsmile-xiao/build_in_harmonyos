# flex

## 简介
flex (Fast Lexical Analyzer Generator) 是一个快速词法分析器生成器，用于生成扫描器（tokenizer）来匹配文本中的模式。常与 bison/yacc 配合使用。

## OHOS 适配
- 使用 autotools 构建系统
- 可能需要更新 config.guess/config.sub 以支持 OHOS 平台
- 当前编译状态：进行中

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
