# nvimpager

Using [neovim](https://github.com/neovim/neovim) as a pager to view man pages,
git diffs, whatnot with neovim's syntax highlighting and mouse support.

The `nvimpager` script calls neovim in a fashion that turns it into something
like a pager. It also has a "cat mode" which prints a highlighted version of
the file to the terminal (like `cat` with neovim syntax highlighting).

## OHOS 适配

- 纯 Bash + Lua 脚本工具，无 C 代码，无 ELF 二进制产物
- 使用 makefile `install-no-man` 目标安装（跳过需要 scdoc 的 man 页构建）
- `VERSION` 显式传入 make，跳过 makefile 解析期的 `./nvimpager -v` 调用
- 安装直接面向 Conan 包目录，使 RUNTIME 路径指向包内正确位置
- 运行时需要 neovim >= 0.9.0（非 Conan 依赖，由目标系统提供）

## 运行时依赖

- neovim >= 0.9.0
- bash

## 用法

```bash
# view a file in nvimpager
nvimpager file
# pipe text to nvimpager
echo some text | nvimpager
# use it as your default $PAGER
export PAGER=nvimpager
man bash
git diff
```

可通过 `NVIMPAGER_NVIM` 环境变量指定 neovim 可执行文件路径。
