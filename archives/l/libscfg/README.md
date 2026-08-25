# libscfg

libscfg 是 emersion 开发的一个小型 C99 库，用于解析与格式化 scfg 配置文件（基于指令、块作用域语法的配置文件格式）。零外部依赖，使用 meson 构建。

- **许可证**: MIT
- **作者**: emersion
- **源码仓库**: https://codeberg.org/emersion/libscfg

## 基本信息

| 属性 | 值 |
|------|-----|
| License | MIT |
| 语言 | C99 |
| 构建系统 | meson |
| 当前版本 | 0.2.0 |
| 类型 | 共享库 |

## 安装产物

- **共享库**: `libscfg.so`
- **头文件**: `scfg.h`
- **pkg-config**: `scfg.pc`

## 核心功能

libscfg 提供以下核心 API：
- `scfg_load_file()` — 从文件加载 scfg 配置
- `scfg_store_file()` — 将 scfg 配置写入文件
- `scfg_parse_file()` — 解析 scfg 配置文件
- `scfg_format_file()` — 格式化输出 scfg 配置
- `scfg_block_finish()` — 结束当前配置块

## HarmonyOS 平台注意事项

1. 构建时必须使用 CC wrapper 自动签名 ELF 二进制（meson sanity check 要求）
2. 上游 meson.build 设 `werror=true`，需加 `-Wno-error=unused-command-line-argument` 抑制 OHOS profile 注入的 `-Wl,--code-sign` 链接器标志警告
3. 验证方式为 pkg-config 检查 + 实际 C 程序链接运行，无命令行工具
