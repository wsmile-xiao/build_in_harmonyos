# makefile2graph

Creates a graph of dependencies from GNU-Make.

Output can be generated for the following formats:

- Graphviz/dot
- Gexf-XML
- PlantUML
- Mermaid
- or a list of the deepest independent targets that should be made.

Notice that sub-makefiles are not supported.

## 编译信息

- **官方主页**: https://github.com/lindenb/makefile2graph
- **构建系统**: Makefile
- **编译器**: clang
- **依赖**: 无外部依赖（需要 GNU install 命令）

## 已编译版本

- master (2026-04-20) - 状态: built

## 使用方法

```bash
# 基本用法
make -Bnd | make2graph

# 输出为 Graphviz DOT 格式
make -Bnd | make2graph --format d

# 输出为 Mermaid 格式
make -Bnd | make2graph --format M

# 输出为 XML 格式
make -Bnd | make2graph --format x

# 列出所有目标
make -Bnd | make2graph --format L
```

## 注意事项

在 OpenHarmony 系统上，需要确保有 GNU install 命令：
- 可以使用预装的 `ginstall` 命令
- 或创建符号链接：`ln -sf ~/usr/local/bin/ginstall ~/usr/local/bin/install`