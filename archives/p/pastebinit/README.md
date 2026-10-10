# pastebinit

## 简介

pastebinit 是一个命令行 pastebin 客户端，用于将文本发送到各种 pastebin 服务（如 paste.debian.net、pastebin.com 等）。

## 可用版本

| 版本 | 状态 | 构建系统 |
|------|------|----------|
| 1.8.0 | built | Make (msgfmt) |

## OHOS 适配

- 纯 Python3 脚本工具，无 C/C++ 编译步骤
- 使用 msgfmt 编译 .po 翻译文件为 .mo
- 依赖 distro 模块用于检测 OS 并设置默认 pastebin
- 上游 Makefile 使用 `install` 命令（OHOS 无 coreutils install，conanfile 改用 shutil 手动打包）

## 依赖

- distro/1.9.0（运行时依赖，用于 OS 检测）

## 功能验证

```bash
pastebinit -h    # 显示帮助
pastebinit -v    # 显示版本
pastebinit -l    # 列出支持的 pastebin 服务
```

## 参考

- 上游仓库：https://launchpad.net/pastebinit
- Debian 包：https://salsa.debian.org/debian/pastebinit
