# libdotconf

配置文件解析库，提供简单灵活的 C 语言接口，用于读取和解析 dot-conf 格式的配置文件。

## 基本信息

| 项目 | 值 |
|------|-----|
| 名称 | libdotconf |
| 版本 | 1.4.1-r0 |
| 构建系统 | autotools |
| 源码仓库 | https://github.com/williamh/dotconf |
| 许可证 | LGPL-2.1 |

## 功能特点

- 支持 ARG_STR/ARG_INT/ARG_TOGGLE/ARG_LIST/ARG_RAW/ARG_NONE 等多种参数类型
- 大小写不敏感选项名匹配 (CASE_INSENSITIVE)
- 回调式 API (DOTCONF_CB)
- Include 指令支持配置文件嵌套
- Here-document 支持
- 环境变量替换
- 上下文敏感性 (context_t)
- 错误处理器注册

## 鸶蒙平台适配状态

| 版本 | 状态 | 功能测试 | 日期 |
|------|------|---------|------|
| 1.4.1-r0 | published | ✅ 25/25 通过 | 2026-06-02 |

## 平台适配要点

- HMDFS setgid 文件系统上 mktemp -d 创建的目录权限不兼容，需替换为 mkdir
- 原始 tarball 不包含 configure 脚本，需 autoreconf -fi 生成
- 配置文件格式为 `OptionName value`（不使用 `=` 分隔符）