# lua-resty-mail

## 简介

lua-resty-mail 是一个高层次的、易于使用的、非阻塞的电子邮件和 SMTP 库，专为 OpenResty 设计。

## 主要功能

- SMTP 认证、STARTTLS 和 SSL 支持
- 多部分纯文本和 HTML 消息体
- From、To、Cc、Bcc、Reply-To 和 Subject 字段（支持自定义头）
- 支持 "test@example.com" 和 "Name <test@example.com>" 格式的邮件地址
- 文件附件支持

## OHOS 适配

### 适配要点

1. 这是纯 Lua 库，无需编译，仅需安装 Lua 模块文件
2. 安装路径：`$PREFIX/share/lua/5.1/resty/mail/`
3. 运行依赖：OpenResty 环境（nginx + ngx_lua 模块）
4. 不需要 ELF 签名（无二进制文件）

### 与 Linux 的差异

- 安装方式相同，通过 Lua package.path 加载
- 需要确保 OpenResty 正确安装
- 无系统级差异

## 依赖关系

### 编译依赖
- 无（纯 Lua 库）

### 运行依赖
- OpenResty 环境
- nginx + ngx_lua 模块
- Lua 5.1/LuaJIT

## 参考资料

- 官网：https://github.com/GUI/lua-resty-mail
- LuaRocks：https://luarocks.org/modules/GUI/lua-resty-mail
- OPM：https://opm.openresty.org/package/GUI/lua-resty-mail/
- 许可证：MIT License

## 版本索引

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.2.0 | built | 2026-06-11 | 最新稳定版，手动安装 Lua 模块 |