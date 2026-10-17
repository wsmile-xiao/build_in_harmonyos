# libapreq2

## 简介
Apache HTTP Server Request Library，用于解析 HTTP Cookie、查询串和 POST 数据，基于 APR/apr-util 构建。

## OHOS 适配
- autotools：显式 `--build/--host` 为 gnu 三元组，绕过旧 config.guess 对 HongMeng 内核的识别失败（原生构建 build==host）
- 上游 configure 强制要求 apache2 apxs + httpd 二进制，OHOS 无 httpd 配方时用构建目录假 apxs/httpd 包装满足版本探测，只构建 C 库部分，关闭 perl glue
- apr-util/1.6.3 仓内无 conan 配方时私有静态子构建并合入 `libaprutil-1.a`（serf/1.3.10 同款模式）

## 依赖
- apr/1.7.6（已发布，直连）
- expat/2.8.2（已发布，供私有 apr-util `--with-expat`）
- apr-util/1.6.3（私有子构建，不走远端 requires）
- 编译工具：clang，autotools

## 参考
- 上游主页：https://httpd.apache.org/apreq/
- 源码仓库：https://github.com/apache/apreq
