# xlinks

Links is a text-terminal web browser for viewing web pages from a terminal.

## 功能概述

- 以文本模式访问和呈现网页，支持 HTTP 页面及重定向。
- 提供 `links` 终端命令；此移植不包含图形界面。

## HarmonyOS PC 适配

- 为 HarmonyOS PC aarch64 构建 Conan 包 `xlinks/2.30`，安装命令为 `links`。
- 仅启用文本终端模式，使用 `--disable-graphics --without-x` 关闭图形和 X11 驱动，并静态链接终端可执行文件。
- TLS 与 zlib 压缩使用 Conan 提供的 OpenSSL 和 zlib；Brotli 压缩未启用。

## 依赖关系

- 编译及运行依赖：`openssl/3.5.8.1`、`zlib/1.3.2.1`。
- 上游许可证为 GPL-2.0-or-later，并包含 OpenSSL 链接例外。

## 参考资料

- 官方网站：[https://links.twibright.com/](https://links.twibright.com/)
- Links 2.30 源码：[官方发布压缩包](https://links.twibright.com/download/links-2.30.tar.gz)
