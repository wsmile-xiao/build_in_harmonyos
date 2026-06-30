# pgcli 4.5.0 适配笔记

## 编译环境
- 构建系统: pip (Python项目)
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (用于setproctitle C扩展)
- 状态: published

## 编译步骤

pgcli 是一个纯 Python 项目，使用 pip install 安装：

1. `python3 -m pip install pgcli==4.5.0 --target=$STAGING_PREFIX/lib/python3.12/site-packages --no-warn-script-location`
2. 将 site-packages/bin/ 下的脚本移到 bin/
3. 修复脚本 shebang：`#!/data/service/.../python3.12` → `#!/usr/bin/env python3`
4. 对 .so 文件 (setproctitle) 进行 ELF 签名 (objcopy)
5. 对 .so 文件 strip debug symbols (objcopy --strip-debug)
6. 保存 debug symbols 为独立文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip --prefix/--root 组合报错 | pip 不支持同时设置 --home 和 --prefix | 使用 --target 替代，直接指定 site-packages 目录 |
| 2 | entry point 脚本不在 bin/ | pip --target 将脚本安装到 site-packages/bin/ | 手动 cp 到 bin/ 并修复 shebang |
| 3 | shebang 硬编码系统路径 | pip 生成的脚本使用绝对路径 | sed 替换为 `#!/usr/bin/env python3` |
| 4 | 系统内存不足 | pip install + ohc-run.py package 一起运行导致 OOM | 分步执行，手动打包 |

## 源码修改

无源码补丁（纯 Python 项目，使用 pip install 方式）

## 依赖版本

- python3: 3.12.8
- pip: 24.3.1
- pgcli 依赖: click 8.4.1, configobj 5.0.9, Pygments 2.20.0, prompt_toolkit 3.0.52, psycopg 3.3.4, pgspecial 2.2.1, sqlparse 0.5.5, cli_helpers 2.15.0, setproctitle 1.3.7, tabulate 0.10.0, wcwidth 0.8.1, tzlocal 5.3.1, typing-extensions 4.15.0

## 验证结果

pgcli --version 输出 4.5.0 版本信息（需 PostgreSQL 服务器才能完整功能验证）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pgcli-4.5.0-ohos-aarch64.tar.gz | ~6.3MB | Release包（含stripped .so） |
| pgcli-4.5.0-ohos-aarch64-debug.tar.gz | ~6.4MB | Debug包（含debug symbols） |

## 注意事项

- pgcli 是纯 Python CLI 工具，需要 PostgreSQL 服务端才能完整使用
- setproctitle 包含 C 扩展(.so)，需要 ELF 签名才能在鸿蒙上执行
- 所有依赖通过 pip 一同安装，打包时包含全部依赖
---

**编译结束**: 2026-06-09 22:25
**最终状态**: built
