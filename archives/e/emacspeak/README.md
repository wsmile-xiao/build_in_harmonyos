# Emacspeak

> Speech interface for Emacs — auditory desktop for visually impaired users

## 简介

Emacspeak 是 Emacs 的语音界面扩展包，为视觉障碍用户提供完整的听觉桌面环境。它通过语音合成将 Emacs 的编辑、浏览和系统管理功能转化为听觉体验，是世界上最早的听觉桌面实现之一。

## OHOS 适配要点

- Emacs Lisp 扩展包，无需传统编译
- Byte compilation 无法在 OHOS 上执行（缺少 Emacs 运行时）
- .el 文件可直接由 Emacs 加载，不需要 .elc
- 安装方式为复制整个目录结构到 share/emacspeak/
- 244 个 .el 文件完整性验证通过

## 参考

- [官方主页](https://emacspeak.sourceforge.net/)
- [源码仓库](https://github.com/tvraman/emacspeak)