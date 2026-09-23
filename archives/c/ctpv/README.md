# ctpv

ctpv 是一个使用 C 编写的终端文件预览器，可根据文件扩展名和 MIME 类型选择文本、目录、图片、归档等预览后端。

## 功能概述

- 输出文本文件和目录预览
- 使用 libmagic 识别文件 MIME 类型
- 为 lf 等终端文件管理器提供预览、清理和退出命令
- 支持 Kitty、Chafa 与 ueberzug 图片预览后端
- 支持 XDG 配置目录和缓存目录

## OHOS 适配

- 使用 OHOS Clang 构建 AArch64 静态 PIE 可执行文件
- 构建期生成器由宿主编译器构建，避免交叉编译时执行目标架构工具
- 临时 IPC 与 Kitty 状态文件遵循 `TMPDIR`，兼容 `/tmp` 不可写的环境
- 默认 shell 从 `SHELL` 获取并回退到 `sh`，不依赖固定的 `/bin/sh` 路径
- 将 `ctpvclear` 构建为原生目标程序，避免安装命令依赖目标系统不存在的 `/bin/sh` shebang
- 串行执行上游 Makefile，避免不支持 FIFO 的文件系统触发并行 jobserver 问题

## 依赖关系

- `libmagic/5.48`：文件 MIME 类型识别及 magic 数据库
- `openssl/3.5.6.1`：MD5 缓存键计算所需的 libcrypto
- 文本预览至少需要系统提供 `sh` 和 `cat`；其他预览后端按需安装

## 参考资料

- 上游源码仓库：https://github.com/NikitaIvanovV/ctpv
- 上游使用说明：https://github.com/NikitaIvanovV/ctpv/blob/v1.1/README.md
