# dehydrated

dehydrated 是 dehydrated-io 项目的 ACME v2 客户端（Let's Encrypt、ZeroSSL 等），
以单个自包含 Bash 脚本实现 ACME 账户注册、域名验证（http-01/dns-01/tls-alpn-01）、
证书签发与续期，不依赖任何编译型组件。

## 功能概述

- ACME v2（及兼容服务器）证书签发、续期、吊销
- http-01 / dns-01 / tls-alpn-01 挑战验证，支持通配符（dns-01）
- RSA / ECC 多算法密钥，多域名 SAN 证书
- 灵活的 hook 脚本机制（部署、DNS provider 接入）
- 纯 Bash 4+ 实现，仅依赖 coreutils + curl + openssl

## OHOS 适配

- 纯 Bash 脚本应用，无编译产物，走脚本打包路径（build_system: none）
- 运行时依赖闭包（OHOS PC 已实测齐备）：bash 5.3.0、curl 8.8.0、openssl 3.0.9、
  gawk 5.4.0、toybox（sed/grep/diff/mktemp 等）、hexdump（/data/service/hnp/bin）
- 脚本以 `OSTYPE=$(uname)` 判定 OS：设备返回 "HarmonyOS" != "Linux"，
  `_sed()` 走 `sed -E`（ERE）分支，toybox sed 两种模式均支持，已实测
- `openssl.cnf` 路径在证书操作时经 `openssl version -d` 探测，无需适配
- `getent` 在 OHOS 缺失：仅影响可选的 DEHYDRATED_USER/DEHYDRATED_GROUP 降权特性
- OHOS hnp bash 在部分执行上下文 getcwd() 失败导致内置 `PWD` 未定义
  （脚本 `set -u` 下 `${PWD}` 引用报错）；自检/测试时显式传 `PWD=<目录>` 规避

## 依赖关系

- 运行依赖：bash >= 4、curl、openssl、sed、awk、grep、diff、mktemp、cut、head、tail、hexdump
- 编译依赖：无

## 参考资料

- 官网：https://dehydrated.io
- 源码：https://github.com/dehydrated-io/dehydrated
- 许可证：MIT
