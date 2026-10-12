# imenu-list — OpenHarmony 编译档案

## 软件简介
imenu-list 是 Bar Magal 的 GNU Emacs 包：把当前缓冲区的 imenu 条目
（函数/变量/章节定义大纲）显示在独立缓冲区 "*Ilist*" 中，支持折叠展开、
 RET 跳转、随缓冲区实时更新，可选联动 hideshow 折叠与 eglot LSP 定位。
**单文件 Emacs Lisp 包**：imenu-list.el（686 行，Package-Requires:
cl-lib 0.5），无任何 C/C++ 源码、无构建系统、无测试套件。许可证
GPL-3.0-or-later。版本 0.9。

注意：大赛任务标签为 C++，实为 Emacs Lisp 包（发行包内无 C/C++ 代码），
按已合入的 web-mode 17.3.20 单文件 elisp 先例适配；如需确认可与小助手
核对。

## OHOS 适配要点
- web-mode 先例范式：`requires("emacs/29.1")`（Emacs 既是字节编译工具链
  也是运行期宿主），`build()` 为防漂移校验 + `emacs -Q --batch -f
  batch-byte-compile`，`package()` 装 .el/.elc 到
  `share/emacs/site-lisp/imenu-list-0.9/`
- 字节编译对 GNU Emacs 29.1 零 Error（仅 point-at-bol 废弃警告与
  hs-toggle-hiding/eglot-* 可选依赖未定义警告，上游固有，无需 patch）
- 上游 v0.9 发行包不含测试套件，以功能级消费者探针代替（8 断言：
  feature 加载、缓冲区名默认值、minor-mode 定义与 batch 下开关实测、
  smart-toggle、position/size 定制变量与默认值）
- 上游 tag 名带 v 前缀（v0.9）：裸 "0.9" 归档 URL 404，conandata 必须写
  v0.9（sha256 双源实测一致）

## 依赖关系
- conan 依赖：emacs/29.1（ohpcd 制品仓已发布，传递依赖 ncurses/6.5）
- 运行期 Emacs 侧依赖：cl-lib 0.5（Emacs 29 内置满足）；可选联动
  hideshow/eglot 不在打包范围
- 被依赖：无

## 参考资料
- [GitHub: bmag/imenu-list](https://github.com/bmag/imenu-list)
- [MELPA: imenu-list](https://melpa.org/#/imenu-list)
