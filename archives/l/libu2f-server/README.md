# libu2f-server

U2F/FIDO2认证服务器库，支持硬件密钥认证

## 功能特性

- 提供U2F服务器端实现
- 支持FIDO2协议
- 支持硬件安全密钥
- 提供认证和注册功能

## OHOS适配

- 使用autotools构建系统
- 需要处理musl libc链接问题
- 添加LDFLAGS="-Wl,--allow-shlib-undefined"

## 参考

- 主页: https://github.com/Yubico/libu2f-server