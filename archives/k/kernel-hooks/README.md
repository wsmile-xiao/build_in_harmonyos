# kernel-hooks

Alpine Linux 的 kernel-hooks 包，用于在 `/lib/modules/*` 更新时执行用户提供的钩子脚本。

## 简介

`kernel-hooks` 提供一套机制：当内核包或提供内核模块的包被安装、升级或移除时，
`/etc/kernel-hooks.d/` 下的可执行脚本会被依次调用，参数为 `<kernel-flavor> <new-version> [<old-version>]`。

## 上游信息

- 项目主页：https://gitlab.alpinelinux.org/alpine/aports/
- 源码位置：`main/kernel-hooks/`
- 适配版本：0.3
- 许可证：MIT

## 说明

`kernel-hooks` 为纯 Shell 脚本集合，无编译过程。上游的触发机制依赖 APK 的 trigger 特性，
在鸿蒙 + Conan 环境下不自动激活，trigger 脚本作为参考文件保留在 `share/kernel-hooks/` 下。
