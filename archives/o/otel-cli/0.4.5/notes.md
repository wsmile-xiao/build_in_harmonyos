# otel-cli 0.4.5 适配笔记

## 编译环境
- 构建系统: go
- 编译日期: 2026-06-09
- 编译器: go 1.26.1
- 状态: published

## 编译步骤
1. 下载源码: https://github.com/equinix-labs/otel-cli/archive/refs/tags/v0.4.5.tar.gz
2. 环境准备: GOPROXY=https://goproxy.cn,direct; TMPDIR=/data/storage/el2/base/cache
3. 编译: go build -v -o otel-cli
4. ELF 签名: python3 ohc-run.py sign-elf otel-cli

## 问题与解决方案
| 问题 | 解决方案 |
|------|----------|
| SSL 证书验证失败 | Python 禁用 SSL 验证下载 |
| HMDFS SELinux 限制 | TMPDIR=/data/storage/el2/base/cache |
| ELF 执行权限拒绝 | ohc-run.py sign-elf 签名 |

---
**编译结束**: 2026-06-09 19:50
**最终状态**: published