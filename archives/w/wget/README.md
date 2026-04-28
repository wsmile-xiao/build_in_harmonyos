# GNU Wget

## 简介
非交互式网络下载工具，支持 HTTP、HTTPS 和 FTP 协议，支持断点续传、递归下载、镜像网站等功能。相比 toybox wget 功能更完整。

## OHOS 适配
- 替代 toybox wget，功能更完整（支持 -q、-c、-r、-m 等参数）
- SSL 需配合 --no-check-certificate 使用（缺少系统 CA 证书）
- musl libc 未实现 secure_getenv()，需降级为 getenv（E081）
- HMDFS 上 umask 077 && mktemp -d 导致目录权限问题（E085）
- config.guess/config.sub 位于 build-aux/ 子目录
- 官方测试 98/124 通过，9 个 HTTPS 证书测试失败（环境问题）

## 依赖
- openssl
- zlib

## 功能验证
```bash
wget --version
wget https://example.com
```

## 参考
- 官网: https://www.gnu.org/software/wget/
