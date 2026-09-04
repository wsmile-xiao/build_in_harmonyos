# aria

aria 是一个用 C89 编写、可嵌入应用程序的轻量级 Lisp 风格语言解释器。

## 功能概述

- 支持数字、符号、字符串、序对、lambda 和宏。
- 提供带文件名和行号的错误回溯。
- 提供异常式错误处理、垃圾回收和 C API。

## OHOS 适配

- Conan 配方直接使用 OHOS profile 提供的 clang、ar 和 ranlib 编译静态库。
- 上游 `build.sh` 固定调用 `/bin/bash` 和 `gcc`，未作为配方入口使用，以适配 OHOS 工具链。
- 上游未提供正式测试套件；适配后的 `test_package` 通过 Conan 消费者真实调用 C API。

## 依赖关系

无外部 Conan 依赖。

## 参考资料

- 上游仓库：https://github.com/rxi/aria
- 许可证：MIT
