# chibi-scheme

## 简介
chibi-scheme 是一个小巧的 Scheme 实现，可用作 C 扩展语言。

## OHOS 适配
- 使用自定义 Makefile 构建，configure 脚本只是提示信息
- 无需补丁，源码无需任何修改即可编译
- 平台检测通过 Makefile.detect 自动完成

## 依赖
无外部依赖。

## 功能验证
```bash
chibi-scheme -e '(display "Hello from chibi-scheme!\n")'
# Hello from chibi-scheme!
```

## 参考
- 官网: https://github.com/ashinn/chibi-scheme
