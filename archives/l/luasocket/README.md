# luasocket

## 软件简介
LuaSocket 是 Lua 语言的网络支持扩展库，提供 TCP/UDP 套接字、HTTP/FTP/SMTP 客户端、URL 解析和 MIME 编解码能力。它构建为 Lua C 扩展模块（.so），由 Lua 宿主解释器在运行时通过 require() 动态加载。

本目录为 luasocket 2.0.2——Lua 5.1 时代的主版本（LuaSocket 2.0.2 + MIME 1.0.2），与仓内 `lua-socket/3.1.0`（上游 3.x 更名后的包，面向 Lua 5.4）是同一上游的不同主版本，包名不同、互不冲突。

## 基本信息
- 官方网站: https://lunarmodules.github.io/luasocket/
- 源码仓库: https://github.com/lunarmodules/luasocket
- 许可协议: MIT License

## 特性
- TCP/UDP 套接字（socket.core）：connect/bind/listen/accept/send/receive/select
- DNS 解析（socket.dns）
- HTTP/FTP/SMTP/TP 客户端（socket.http 等 Lua 层实现）
- URL 解析/构造（socket.url，独立模块）
- MIME 编解码（mime.core：base64/quoted-printable）
- LTN12 数据传输过滤器（ltn12）

## 编译版本
- 2.0.2: ✅ 已编译（clang + lua/5.1，老式 Makefile 变量注入）

## 编译要点
1. **构建系统**: 老式 Makefile（顶层 makefile + src/makefile，config 文件驱动），无 configure
2. **变量注入**: `CC/LD/LUAINC/CFLAGS/LDFLAGS` 可在 make 命令行覆盖（与 3.x 的 CC_linux/LD_linux 不同）
3. **编译器**: 必须使用 clang（鸿蒙系统无 gcc），从 Conan conf 获取（R33）
4. **依赖**: lua/5.1（Conan 制品仓已发布）
5. **链接**: C 扩展模块为纯 -shared 对象，不链 -llua（Lua 符号由宿主在 dlopen 时解析）
6. **安装**: INSTALL_TOP_SHARE/INSTALL_TOP_LIB 变量指定目标（非 3.x 的 DESTDIR+prefix）

## 使用场景
- Lua 5.1 应用的网络编程（TCP 服务/客户端、UDP）
- 需要在鸿蒙 PC 上运行依赖 LuaSocket 2.x 的传统 Lua 应用
- 与 lua-socket 3.x 按目标 Lua 版本二选一使用
