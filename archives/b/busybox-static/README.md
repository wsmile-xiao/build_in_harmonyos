# BusyBox (static)

BusyBox 1.36.1 — statically linked multicall binary combining tiny UNIX utilities.

Homepage: https://busybox.net/

## 与 busybox 的区别

`busybox-static` 使用 `CONFIG_STATIC=y` 构建完全静态链接的二进制，适用于嵌入式、initramfs 和急救环境，无需运行时共享库依赖。
