# Smex — Emacs M-x Enhancement | OpenHarmony 编译档案

## 软件简介
smex 是 Emacs 编辑器的 M-x 命令增强工具，基于 Ido 提供模糊匹配功能。它能按最近使用和最频繁使用的顺序排列命令，让用户更快捷地找到并执行所需命令。

## 功能概述
- Ido 风格的模糊匹配（输入 'lnmd' 匹配 'line-number-mode'）
- 按最近使用和频率排序命令
- 支持仅显示当前 major-mode 相关命令（smex-major-mode-commands）
- 命令历史持久化（~/.smex-items）
- 自动检测新命令并更新缓存

## OHOS 适配要点
- smex 是纯 Emacs Lisp 包，无构建系统（无 configure/make/cmake）
- Conan recipe 的 package() 仅复制 smex.el 到 share/emacs/site-lisp/
- 包与 OS/arch 无关（package_id 使用 self.info.clear()）
- 运行时依赖 Emacs 编辑器（非 Conan 依赖，由用户提供）

## 依赖关系
- Emacs 24+（运行时依赖，由用户提供）

## 使用方式
在 Emacs 配置文件（.emacs / init.el）中添加：
```elisp
(require 'smex)         ; 如果使用 package.el 则不需要
(smex-initialize)        ; 可省略，首次运行时自动初始化

(global-set-key (kbd "M-x") 'smex)
(global-set-key (kbd "M-X") 'smex-major-mode-commands)
(global-set-key (kbd "C-c C-c M-x") 'execute-extended-command) ; 旧 M-x
```

## 安装路径
- smex.el 安装到 `share/emacs/site-lisp/smex.el`

## 参考资料
- [smex GitHub 仓库](https://github.com/nonsequitur/smex)
- [Emacs Lisp 包管理](https://www.emacswiki.org/emacs/InstallingPackages)
