# mongoose

## 简介
mongoose 是 Cesanta 开发的嵌入式 Web 服务器 C/C++ 库，提供 HTTP/HTTPS/MQTT/WebSocket 等协议支持，体积小巧，适合嵌入到应用程序中提供网络服务能力。

## OHOS 适配
- Makefile 构建，支持静态库和共享库两种模式
- 静态库（libmongoose.a）功能完整，推荐使用
- 共享库（libmongoose.so）运行时有 ELF 签名问题（平台限制）
- 核心 API 全部验证通过：mg_match, mg_mgr_init, mg_http_listen, mg_http_reply, mg_str
- HTTP 服务器在静态库模式下启动并运行成功（监听端口19999）

## 依赖
- 编译依赖：clang（C编译器）
- 可选依赖：OpenSSL（SSL/TLS支持）
- 无运行时依赖（静态库模式）

## 功能验证
```bash
# 检查库安装
ls -la $HOME/usr/local/lib/libmongoose*
ls -la $HOME/usr/local/include/mongoose.h

# 验证版本（C程序中）
MG_VERSION  # 输出: 7.21

# 验证 HTTP 服务器（链接静态库）
clang test_mongoose.c -I$HOME/usr/local/include -L$HOME/usr/local/lib -lmongoose -o test_mongoose
./test_mongoose  # HTTP 服务器启动
```

## 已知限制
- 共享库（libmongoose.so）运行时有 ELF 签名问题
- 推荐使用静态库（libmongoose.a）部署

## 参考
- GitHub: https://github.com/cesanta/mongoose
- 文档: https://mongoose.ws/documentation/