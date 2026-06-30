# Lua Tableshape

## 简介

Lua Tableshape 是一个用于表结构验证和形状定义的 Lua 库。它提供了一种声明式的方式来定义表的结构,并验证表是否符合预期的形状。

## 功能

- 类型检查和验证
- 形状定义和匹配
- 可选字段支持
- 嵌套表结构验证
- 扩展功能(luassert、JSON Schema)

## OHOS 适配

- **纯 Lua 模块**: 无需编译,直接安装 Lua 文件
- **安装路径**: `$PREFIX/share/lua/5.4/tableshape/`
- **无需 ELF 签名**: 无二进制文件
- **测试验证**: 已通过基本功能测试

## 依赖

### 编译依赖
- lua 5.4

### 运行依赖
- lua 5.4

## 已知问题

无

## 参考资料

- 官网: https://github.com/leafo/tableshape
- 文档: https://github.com/leafo/tableshape#readme