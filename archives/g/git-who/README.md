# git-who

git-who 是一个命令行工具，回答那个永恒的问题："这段代码是谁写的？！"

与 `git blame`（告诉你某一行代码是谁写的）不同，git-who 告诉你一个组件或子系统整体由谁负责——可以把它理解为"针对文件树的 git blame"。

## 功能概述

- 按作者统计代码贡献（提交数、修改文件数、增删行数），输出贡献表格
- 支持按路径、分支、tag、commit 区间统计
- `tree` 子命令：目录/文件树视图，标注每个路径最主要的贡献者
- `hist` 子命令：提交活跃度时间线柱状图
- 支持排序（最近编辑/首次编辑/提交数/文件数/行数）、作者/日期/路径过滤
- 可作为 git 子命令使用：`git who`
- 遵循 NO_COLOR 规范（v1.3 新增）

## OHOS 适配

- 纯 Go 项目，`CGO_ENABLED=0` 静态编译，无 C 依赖，无平台分支代码
- hmbs 预检沙盒不注入 go 工具链：配方先探测设备 go，找不到则下载固定版本 Go SDK（go1.23.8 linux-arm64）
- OHOS 上所有被 fork/exec 的 ELF（go/gofmt/pkg/tool 及 go test 临时二进制）必须带 `.codesign` 段，否则被 Seccomp 拦截
- Go linker 在 hmdfs 上 mmap 输出失败，链接输出放到非 hmdfs 工作区
- 版本号通过 `-ldflags -X main.Version=1.3 -X main.Commit=aa656b0` 注入

## 依赖关系

- 编译依赖: Go SDK ≥ 1.23（配方自备 go1.23.8），doublestar/v4、go-cmp、go-runewidth、x/term、x/sys、uniseg
- 运行依赖: git（工具运行时通过 subprocess 调用 git 命令）

## 参考资料

- 上游仓库: https://github.com/sinclairtarget/git-who
- 版本: v1.3 (2026-01-24)
- License: MIT
