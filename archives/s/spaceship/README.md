# spaceship

Spaceship 是一个极简、强大且高度可定制的 Zsh 提示符主题。

## 简介

Spaceship Prompt 是一个最小化设计、功能强大的 Zsh 提示符，能够显示：
- Git 和 Mercurial 仓库状态
- 各种语言运行环境（Node.js, Rust, Python, Ruby, Swift, Go, PHP 等）
- Docker 版本和 Kubernetes context
- 包版本信息（npm, cargo, composer 等）
- 电池状态和电量
- 后台任务指示器 `✦`

## 鸿蒙适配说明

### 依赖
- **Zsh v5.2+**（鸿蒙预装 Zsh 5.9，满足要求）
- **Powerline Font 或 Nerd Font**（推荐 Fira Code）

### 已知限制
- 部分 Zsh 模块缺失（zsh/mathfunc, zsh/zpty），不影响基本功能
- add-zsh-hook 函数需要手动加载

### 安装方式
纯脚本项目，无需编译。安装后需要在 `.zshrc` 中添加：

```zsh
source /usr/local/share/spaceship-prompt/spaceship.zsh
```

### 编译产物
- 包含编译后的 .zwc 文件，提高加载速度
- 共 171 个文件（84 个 .zsh + 85 个 .zwc + 其他）

## 编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 4.22.3 | published | 2026-06-10 | 最新稳定版 |

## 更多信息

- 官网: https://spaceship-prompt.sh
- GitHub: https://github.com/spaceship-prompt/spaceship-prompt
- 文档: https://spaceship-prompt.sh/getting-started