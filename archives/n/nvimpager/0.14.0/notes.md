# nvimpager 0.14.0 适配笔记

## 软件简介
nvimpager 使用 neovim 作为分页器，查看 man 手册、git diff 等，带 neovim 的语法高亮
和鼠标支持。纯 Bash + Lua 脚本项目，无 C 代码，无 ELF 二进制产物。

## 构建系统
- Makefile 驱动；`install-no-man` 目标安装脚本与 Lua 运行时（跳过需要 scdoc 的 man 页）
- 原生支持 `PREFIX` 与 `DESTDIR` 变量

## 适配要点
1. **纯脚本工具**：无编译步骤，安装即配置脚本 + 拷贝 Lua 模块。
2. **RUNTIME 路径**：makefile 通过 sed 将脚本中的 `RUNTIME=` 行替换为
   `$(PREFIX)/share/nvimpager/runtime`。配方直接安装到 `self.package_folder`，
   使烘焙进脚本的 RUNTIME 路径指向 Conan 缓存中的正确位置。
3. **VERSION 注入**：makefile 默认在变量展开期调用 `./nvimpager -v`（需 bash）获取
   版本号。配方显式传入 `VERSION=0.14.0`，跳过该调用，消除构建期对 bash 的依赖。
4. **无补丁**：上游 makefile 已原生支持 PREFIX，无需任何补丁。
5. **平台兼容**：shebang `#!/usr/bin/env bash` 在 OHOS 上通过 PATH 解析 bash。

## 测试
- 上游测试基于 busted + neovim，OHOS 构建环境不可用，标记为 skipped。
- test_package 冒烟测试：`nvimpager -v` 与 `nvimpager -h`，二者均在调用 neovim 前
  退出，因此无需 neovim 即可运行。

## 运行时依赖
- neovim >= 0.9.0（运行时必需，非 Conan 依赖，由目标系统提供）
- bash（执行脚本）
- 可通过 `NVIMPAGER_NVIM` 环境变量指定 neovim 可执行文件路径
