# libhtp

## 简介
libhtp 是一个高性能的 HTTP 解析库，设计用于安全分析和流量监控。

## OHOS 适配
- 需要运行 autogen.sh 生成 configure 脚本
- HMDFS umask 问题：修改 configure 中 umask 077 → 022
- 使用 hints/post-download.sh 自动化处理

## 依赖
- zlib
- iconv

## 功能验证
pkg-config --modversion htp 返回 0.5.53

## 参考
- https://github.com/OISF/libhtp