# web-mode 17.3.20 适配笔记

## 环境与构建

- 目标平台：HarmonyOS PC arm64
- 构建系统：Emacs Lisp batch byte compilation
- 构建依赖：`emacs/29.1`
- 产物：`web-mode.el` 与 `web-mode.elc`
- 上游源码标签：`v17.3.20`，commit `0c83581d1e93d1d802c730a1d5e90cd1c740e1b2`

## W0 依赖检查

在隔离 Conan HOME 中从官方 `ohpcd` Remote 成功下载并以 OHOS/armv8
profile、`--build=never` 安装 `emacs/29.1` 二进制；其传递依赖为
`ncurses/6.5`。

## 上游测试

上游 `run.sh` 加载 `web-mode.el` 后调用 `web-mode-test`。该函数遍历
`tests/` 中 31 个 fixture，对每个文件执行 web-mode 缩进，并比较缩进前后
MD5，以验证格式化幂等性。配方运行同一上游入口，并在发现 `_err.*` 失败
产物时中止构建，避免上游脚本因仅打印 `ko` 而错误返回成功。

## 消费者测试

`test_package` 使用被测包导出的 `WEB_MODE_LISPDIR`，通过已发布的
`emacs/29.1` 加载打包后的 `web-mode.elc`，执行 8 项功能断言，覆盖版本、
feature、major mode、HTML 内容类型、HTML 语言识别、PHP/Twig 引擎识别和
缩进命令。

## 源码修改

回移上游紧邻 17.3.20 标签的 JSX 缩进修复提交
`f90d44a14bfdef03eb866b3230cd221c9b2ca393`。该补丁修复上游
`tests/test.jsx` 的幂等缩进失败，不修改测试 fixture，也不修改 17.3.20
版本标识；应用后上游测试由 30/31 提升为 31/31。
---

**编译结束**: 2026-08-17 22:23
**最终状态**: built
