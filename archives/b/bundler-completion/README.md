# bundler-completion

## 简介

bundler-completion 提供 Ruby Bundler 命令行（`bundle` / `bundler`）的 bash 自动补全脚本，
来源为开源项目 [mernen/completion-ruby](https://github.com/mernen/completion-ruby) 的
`completion-bundle`。纯 bash 脚本，无需编译。

## OHOS 适配

### 适配要点

1. **无编译流程**：纯 bash 补全脚本，`conan create` 只做下载、校验与安装
2. **安装路径**：`share/bash-completion/completions/bundler`，可被 bash-completion 懒加载
3. **安装名映射**：上游文件名 `completion-bundle` → 命令名 `bundler`（同 Homebrew bundler-completion formula）
4. **依赖 bash-completion**：补全运行时需要 bash-completion 包提供框架函数

### 已知问题

- `bundle exec rake|rails …` 等子命令的参数补全需要上游其余脚本
  （completion-rake/completion-rails），不在本包范围内

## 排除与替代

无排除组件（仅包含一个 completion 脚本）。

## 依赖

### 运行依赖

| 依赖 | 说明 |
|------|------|
| bash-completion | 提供 `_get_comp_words_by_ref`、`_filedir`、`__ltrim_colon_completions` 等补全框架函数 |

### 编译依赖

无编译依赖（纯文本脚本）。

## 功能验证

```bash
# 安装产物
ls $PREFIX/share/bash-completion/completions/bundler

# 语法与注册检查
bash -n $PREFIX/share/bash-completion/completions/bundler
source $PREFIX/share/bash-completion/completions/bundler
complete -p bundler   # → complete -F __bundle ... bundler ...

# 交互式: 输入 bundle <Tab><Tab> 应列出 help/install/update 等子命令
```

## 参考

- 官方仓库: https://github.com/mernen/completion-ruby
- 上游文件: completion-bundle
- 许可证: MIT
