# inheritenv — OpenHarmony 编译档案

## 软件简介
inheritenv 是 Steve Purcell 的 GNU Emacs Lisp 包：解决 Emacs 库在临时缓冲区
中运行后台进程时不继承调用缓冲区局部环境变量（`process-environment` /
`exec-path`）的常见陷阱，提供 `inheritenv` 宏（库作者包装进程执行代码用）与
`inheritenv-add-advice` 宏（用户改造既有命令用）。**纯 Elisp 数据包**：单文件
`inheritenv.el`（87 行）+ ERT 测试 `inheritenv-tests.el`（38 行），无任何
C/C++ 源码。许可证 GPL-3.0-or-later。版本 0.2，要求 Emacs ≥ 24.4。

注意：大赛任务标签为 C++，实为 Emacs Lisp 包（发行包内无 C/C++ 代码），按
ace-link 纯数据包先例适配；如需确认可与小助手核对。

## OHOS 适配要点
- 纯 Elisp 数据包（ace-link 先例范式）：`package()` 把 .el 文件与 README 装到
  `lib/site-lisp/`，Emacs 经 load-path 加载，字节编译留给 Emacs 运行时
- 上游 Makefile 的 compile/package-lint/test 目标需 Emacs 运行时与 MELPA
  网络，配方构建期不执行（R1 参数最少化）；防漂移校验改为行数区间断言
- 测试探针在宿主有 emacs 时**原样运行上游 ERT 测试命令**（`-Q --batch`
  加载 inheritenv.el + inheritenv-tests.el），无 emacs 则跳过并注明

## 依赖关系
- conan 依赖：无（上游运行时依赖 Emacs ≥ 24.4，emacs 包尚未适配）
- 被依赖：无

## 参考资料
- [GitHub: purcell/inheritenv](https://github.com/purcell/inheritenv)
- [MELPA: inheritenv](https://melpa.org/#/inheritenv)
