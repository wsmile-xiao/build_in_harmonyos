# clac

**命令行栈式计算器**（后缀表示法 / RPN，来自 soveran）

clac 是一个命令行、基于栈的计算器，使用后缀（逆波兰）表示法，随时显示栈内容：输入表达式时栈变化实时反映。支持基本算术、模除、`sum`/`add`/`count`、暂存与恢复（`.` `,` `:` `;`）、`roll`、`round`/`floor`/`ceil` 等操作，并支持通过 `CLAC_WORDS` 环境变量加载用户自定义词。

## 用法

```bash
clac 3              # => 3
clac "3 4 +"        # => 7
clac "1 2 3 4 sum"  # => 10
```

不带参数运行 `clac` 进入交互模式（使用内嵌 linenoise 行编辑）。

## 上游

- 主页: https://github.com/soveran/clac
- 许可证: BSD-2-Clause
- 内嵌依赖: linenoise、sds（随官方源码包提供，随包一同构建）
