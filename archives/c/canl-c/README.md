# canl-c

canl-c 是 Common Authentication Library (caNl) 的 C 绑定，提供网格/分布式场景下的
安全连接（TLS）与 X.509 代理证书管理能力。

## 功能概述

- Main API：建立（双向认证的）client-server 安全连接，收发数据；机制插件化
- Certificate API：代理证书的创建、签名与委派
- 异步 DNS 解析（基于 c-ares）
- 附带 4 个工具：emi-canl-server、emi-canl-client（TLS 回环示例）、
  emi-canl-proxy-init（代理证书生成）、emi-canl-delegation（证书委派）

## OHOS 适配

- 构建系统为 EMI 自定义 Makefile + libtool（无 autotools/cmake）
- 构建期依赖 perl（canl_err*.c/h 由 gen_err*.pl 生成）与 bison（*_parse.y），
  经 Conan tool_requires（perl/5.42.2、bison/3.8.2、libtool/2.5.4）提供
- 4 个可移植性补丁：perl 调用、musl netdb 宏兜底、BUILD_DOC 守卫 + 示例依赖头、
  noCertFound 误报修复（详见 patches/ 与 notes.md）
- 运行期 CA 信任用 X509_CERT_DIR 环境变量指定（上游自有机制）

## 依赖关系

- openssl/3.0.16（TLS 机制，静态链入库）
- c-ares/1.34.6（异步 DNS，静态链入库）
- krb5/1.22.1（头文件用途：公开头 canl.h 包含 gssapi.h）

## 参考资料

- 源码: https://github.com/CESNET/canl-c
