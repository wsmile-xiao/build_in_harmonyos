# lemon

## 简介
Lemon 是 SQLite 使用的 LALR(1) 解析器生成器，类似于 yacc/bison。

## OHOS 适配
- 需要手动修改 Makefile
- 单文件工具，编译简单
- 补丁仅修改 Makefile

## 依赖
- 无编译依赖

## 功能验证
```bash
lemon --version  # 或验证二进制可执行
```

## 参考
- 主页: https://www.sqlite.org/src/doc/trunk/doc/lemon.html
