# lua-resty-openidc

[![CI Status](https://github.com/zmartzone/lua-resty-openidc/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/zmartzone/lua-resty-openidc/actions/workflows/docker-ci.yml)

## 简介

**lua-resty-openidc** 是一个用于 NGINX 的 Lua 库，实现了 OpenID Connect Relying Party (RP) 和 OAuth 2.0 Resource Server (RS) 功能。

### 主要功能

- **OpenID Connect Relying Party**: 使用 OpenID Connect Discovery 和 Basic Client Profile（Authorization Code 流程）对用户进行身份认证
- **OAuth 2.0 Resource Server**: 验证 OAuth 2.0 Bearer Access Tokens
- **Session 管理**: 通过 lua-resty-session 提供灵活的会话存储选项（浏览器 cookie、shared-memory、memcache、redis）
- **缓存支持**: Discovery 文档和 Access Tokens 的服务器端缓存
- **反向代理**: 可作为反向代理终结 OAuth/OpenID Connect

## 版本信息

当前版本：1.7.6

### 已编译版本

| 版本 | 状态 | 补丁 | 编译日期 |
|------|------|------|----------|
| 1.7.6 | ✅ published | 1 | 2026-06-10 |

## 依赖

### 运行时依赖

- OpenResty 或 Nginx + lua-nginx-module
- lua-resty-http >= 0.08
- lua-resty-session >= 2.8
- lua-resty-jwt >= 0.2.0（可选，用于 JWT Access Token 验证）

## 安装

### 使用预编译包

通过 cmd-pkgs 安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lua-resty-openidc 1.7.6
```

文件将安装到：`/usr/local/share/lua/5.1/resty/openidc.lua`

### 使用 OPM（OpenResty Package Manager）

```bash
opm install zmartzone/lua-resty-openidc
```

### 使用 LuaRocks

```bash
luarocks install lua-resty-openidc
```

## 补丁说明

### 1.7.6 版本补丁

| 补丁文件 | 用途 | 类型 |
|---------|------|------|
| 0001-Makefile.patch | 为纯 Lua 库创建安装脚本 | 平台适配 |

## 使用示例

### Google+ Signin 配置

```nginx
http {
  lua_package_path '~/lua/?.lua;;';

  resolver 8.8.8.8;
  lua_ssl_trusted_certificate /etc/ssl/certs/ca-certificates.crt;
  lua_ssl_verify_depth 5;

  lua_shared_dict discovery 1m;
  lua_shared_dict jwks 1m;

  server {
    listen 8080;

    location / {
      access_by_lua_block {
        local opts = {
          redirect_uri_path = "/redirect_uri",
          discovery = "https://accounts.google.com/.well-known/openid-configuration",
          client_id = "<client_id>",
          client_secret = "<client_secret>",
          scope = "openid email profile"
        }

        local res, err = require("resty.openidc").authenticate(opts)

        if err then
          ngx.exit(500)
        end

        ngx.req.set_header("X-USER", res.user.sub)
      }

      proxy_pass http://origin-server;
    }
  }
}
```

## 许可证

Apache License 2.0

## 参考链接

- [GitHub 仓库](https://github.com/zmartzone/lua-resty-openidc)
- [OpenResty](http://openresty.org/)
- [OpenID Connect 规范](http://openid.net/specs/openid-connect-core-1_0.html)