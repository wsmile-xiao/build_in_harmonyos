# sqlpage

## 简介
SQLPage 是一个用 SQL 构建网页的 Rust 工具。用户只需编写 SQL 查询，SQLPage 会自动生成交互式网页界面，无需前端开发经验。内置 SQLite 支持，也可连接 PostgreSQL、MySQL 等外部数据库。

## OHOS 适配
- Rust 项目，使用 cargo 构建系统，目标为 `aarch64-unknown-linux-ohos`
- 需要 `.cargo/config.toml` 配置 OHOS 交叉编译工具链（指定 linker、ar 等）
- 需要修改 `Cargo.toml` 和 `Cargo.lock` 调整依赖版本以兼容 OHOS
- 需要修改 `build.rs` 适配 OHOS 构建环境
- 数据库模块（connect、mod、sql、parameter_extraction、sql_to_json）需要适配 OHOS 系统调用差异
- 最终生成静态二进制文件，无外部动态库依赖，便于部署

## 排除与替代
- 无需替代方案，sqlpage 是独立的 Rust 工具

## 依赖
- 编译依赖：rust-toolchain (支持 aarch64-unknown-linux-ohos target)
- 运行依赖：无（静态二进制，自包含 SQLite）

## 功能验证
```bash
# 检查sqlpage二进制
sqlpage --version
# 应输出: sqlpage 0.44.0

# 检查帮助信息
sqlpage --help

# 检查二进制格式
file sqlpage
# 应为: ELF executable, 64-bit LSB arm64, static
```

## 参考
- GitHub仓库：https://github.com/sqlpage/SQLPage
- 官方文档：https://sql-page.com/