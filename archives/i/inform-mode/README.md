# inform-mode — OpenHarmony 编译档案

## 软件简介
inform-mode 是 Inform 6 交互式小说语言的 Emacs 主模式：提供语法高亮、
缩进、函数定位与编译/运行命令集成（调用 inform6 编译器与 frotz 解释器）。
本档案对应 1.6.2 版（2013-10 发布）。**单文件解释型源码包**：发行形式为
inform6 Unix 发行包内的 `contrib/inform-mode.el`（GPL-3.0+），无编译产物
——Debian/Ubuntu 亦从 inform6-compiler 6.42 同源构建 `inform-mode` 二进制
包（all 架构），安装到 `/usr/share/emacs/site-lisp/inform-mode.el`。
许可证为 GPL-3.0-or-later。

## OHOS 适配要点
- 无运行时包（OHOS PC 未移植 Emacs）：`build()` 仅做防漂移校验（文件
  在位 + 63201 字节精确断言），`package()` 将 elisp 安装到
  `share/emacs/site-lisp/`，GPL-3.0 全文随包附于 `licenses/`，
  `package_id` 清空
- 验证以内容级消费者探针代替运行时加载：清单 + 尺寸防漂移 + 版本头/
  功能符号（defun/defvar/defcustom/autoload）+ 许可证文本 + 截断注入负向
- 消费者（Emacs 环境）经 `load-file` 或 site-lisp 路径加载使用；
  环境变量 `INFORMMODE_ELISP_DIR` 指向包内 elisp 目录

## 依赖关系
- 无编译/运行依赖（解释型源码，运行时为 Emacs，非 conan 依赖）
- 被依赖: 无（供 Emacs 用户手动加载，非 conan 依赖）

## 参考资料
- [IF Archive: inform6 source（inform-mode.el 发行所在包）](https://ifarchive.org/indexes/if-archive/infocom/compilers/inform6/source/)
- [Debian inform-mode 二进制包](https://packages.debian.org/trixie/inform-mode)
- [上游 Git 仓库（rupertl/inform-mode）](https://github.com/rupertl/inform-mode)
