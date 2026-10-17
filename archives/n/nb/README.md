# nb

命令行笔记、书签与知识库管理工具，支持加密、搜索、Git 版本化与同步。

## Description

nb 是一个命令行和本地 Web 笔记、书签、归档与知识库应用：

- 纯文本数据存储
- 加密（密码保护笔记与书签）
- 过滤、固定、标签与搜索
- Git 版本化与同步
- 单文件 bash 脚本，开箱即用

## Key Features
- `nb add` — 添加笔记/书签/待办
- `nb ls` — 列出笔记
- `nb show` — 查看笔记
- `nb search` — 全文搜索
- `nb edit` — 编辑笔记
- 支持加密、Git 同步、浏览器集成

## Version Information
- **7.25.4**: 单文件 bash 脚本，prebuilt 部署到 `/system/bin`

## Platform Notes (HarmonyOS PC)
- 纯 bash 脚本，无需编译，直接安装为系统可执行文件
- 通过 `ohos_prebuilt_executable("nb")` 集成到 OpenHarmony 构建
- 依赖系统 bash 运行环境

## Upstream
- 上游仓库: https://github.com/xwmx/nb
- License: AGPL-3.0-or-later
