# zsh-autocomplete 编译笔记

## 编译信息
- 软件名: zsh-autocomplete
- 版本: main (GitHub main branch, 2026-03-26)
- 构建日期: 2026-06-08
- 构建系统: script (纯脚本，无需编译)

## 源码来源
- URL: https://github.com/marlonrichert/zsh-autocomplete
- 方式: GitHub main branch tarball

## 构建过程
此软件为纯 Zsh 脚本插件，不需要编译过程。

### 安装步骤
1. 下载源码: `curl -kL https://github.com/marlonrichert/zsh-autocomplete/archive/refs/heads/main.tar.gz`
2. 解压源码: `tar -xzf zsh-autocomplete-main.tar.gz`
3. 复制文件到目标目录:
   - `zsh-autocomplete.plugin.zsh`
   - `Functions/` 目录
   - `Completions/` 目录
4. 目标路径: `~/.zsh/plugins/zsh-autocomplete/` 或 `/usr/share/zsh/plugins/zsh-autocomplete/`

### 测试
- 测试脚本 `run-tests.zsh` 需要 git 仓库环境
- 插件加载测试在 musl zsh 环境下遇到模块加载问题:
  - `zsh/param/private` 模块不可用
  - `zsh/system` 模块不可用
  - 这些是 zsh 模块问题，非插件本身问题

## 依赖
- zsh >= 5.8 (完整版，含 zsh/param/private 和 zsh/system 模块)
- 建议: 使用完整版 zsh (非 musl 精简版)

## 安装后配置
在 `~/.zshrc` 中添加:
```zsh
source /path/to/zsh-autocomplete/zsh-autocomplete.plugin.zsh
```

然后重启 shell 或执行 `exec zsh`

## 文件列表
- zsh-autocomplete.plugin.zsh - 主入口文件
- Functions/Init/ - 初始化函数
- Functions/Util/ - 工具函数
- Functions/Widgets/ - ZLE 组件
- Completions/ - 补全函数

## 注意事项
- 安装后需要从 .zshrc 中移除 `compinit` 调用（插件会自动处理）
- Ubuntu 用户需要在 .zshenv 中设置 `skip_global_compinit=1`
- Nix 用户需要在 home.nix 中设置 `programs.zsh.enableCompletion = false`

## 编译结束
**最终状态**: built (脚本软件，已安装到目标位置)
