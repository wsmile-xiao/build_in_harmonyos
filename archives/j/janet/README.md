# Janet

Janet 是一门函数式与命令式兼备的编程语言和运行时环境。语法类似 Lisp，融合了 Clojure、Scheme 和 Common Lisp 的特性，同时借鉴了 Python、Ruby 等现代动态语言的设计。

## 主要特性

- Lisp 语法（S-表达式）
- 接近 C 语言的性能
- 一等公民函数与闭包
- 内置异步/事件循环系统（ev）
- FFI（外部函数接口）支持
- 体积小巧、可移植、可嵌入

## OHOS 平台适配说明

- OHOS 与 Android 类似，缺少 `pthread_cancel()` 系统调用，需要使用 SIGUSR1 信号机制替代线程取消
- 补丁 `0001-src-core-ev.c.patch` 将 3 处 `JANET_ANDROID` 条件宏扩展为 `defined(JANET_ANDROID) || defined(__OHOS__)`
- 2 项 OHOS 平台限制性测试失败（不影响核心功能）：
  - `os/execute` 管道写入临时文件（suite-ev.janet:115）
  - Unix Domain Socket SO_REUSEADDR（suite-ev.janet:505）