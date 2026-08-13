# alicloud 1.3.4 适配 notes

## 包信息

- 类型：C++ 静态库（SCons 构建）
- 上游：阿里云 MNS (Simple Message Queue) C++ SDK 1.3.4（2016-12-29 发布）
- 简介：阿里云消息服务 MNS 的 C++ 客户端 SDK，支持队列/主题消息收发
- 依赖：libcurl（HTTP 传输）、openssl（HMAC 请求签名）

## 适配要点

1. **源码获取**：官方发布物为 zip（阿里云文档 CDN），zh-CN 主路径 + en-US 镜像回退
2. **构建系统**：SCons（上游 SConstruct + src/SConscript）
   - `scons` 产出 `lib/libmnscpp.a`，并把头安装到 `include/mns/`
   - 依赖 include/lib 路径通过环境变量 CPPPATH/LIBPATH 注入（PkgConfigDeps 生成 .pc 供 scons 参考）
   - LIBS=curl ssl crypto（mns_network_tool.cpp 用 libcurl，mns_utils.cpp 用 OpenSSL HMAC）
3. **打包**：`include/mns/*.h` + `lib/libmnscpp.a`
4. **依赖**：curl/8.15.0、openssl/3.5.6（制品仓已发布）

## 测试用例

- test_compile：编译一个最小 consumer（include mns_client.h + 链接 libmnscpp.a + curl/openssl）
- test_symbol：检查 libmnscpp.a 导出 MnsClient 构造等关键符号

## 已知限制

- MNS 是云端服务，test_package 无法真实收发消息（无有效凭据），仅验证编译链接与符号
- 上游 2016 年发布，代码较老（pugixml 内嵌、openssl 1.x API），已用 openssl 3.x 兼容性验证
