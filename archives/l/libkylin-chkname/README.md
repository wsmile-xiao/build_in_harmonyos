# libkylin-chkname

libkylin-chkname 是 openKylin 的用户名与用户组名合法性检查库。

## 功能概述

- 检查名称长度、首字符和允许字符集合；
- 拒绝纯数字、十六进制、八进制及特殊点名称；
- 可选地根据随包安装的保留名表拒绝系统账户名；
- 将检查结果转换为可本地化的错误文本；
- 提供带 `extern "C"` 保护的 C API，可由 C 和 C++ 程序使用。

## OHOS 适配

- 使用 Conan OHOS profile 和上游 Autotools 工程构建 AArch64 共享库；
- 固定 Autotools 辅助文件目录，保证所有生成文件留在源码构建树中；
- 为 `autoreconf` 生成的 `config.guess` 补充 HarmonyOS 原生平台识别；
- 保留上游系统资源路径作为默认值，同时由 Conan 运行环境指向包内的
  `reserved-names` 与 locale 数据；
- 不使用 HarmonyOS 专属源码分支，Linux 与 OHOS 共用同一套可移植修改。

## 依赖关系

- 构建工具：Autoconf、Automake、Libtool、gettext；
- 运行依赖：`gettext/0.22.5.1` 提供 libintl。

## 参考资料

- 上游仓库：https://gitee.com/openkylin/libkylin-chkname
- 官方 1.0.10 发布包：https://gitee.com/openkylin/libkylin-chkname/releases/tag/debian%2F1.0.10-1
