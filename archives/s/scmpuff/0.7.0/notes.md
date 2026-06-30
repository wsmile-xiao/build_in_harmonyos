# scmpuff 0.7.0 编译笔记

## 编译过程

1. 安装 Go 1.26.1（USTC 镜像）
2. 签名 Go 工具链
3. 设置 TMPDIR=/data/storage/el2/base/cache
4. make build

## 问题解决

| 问题 | 解决方案 |
|------|----------|
| Go 二进制无法执行 | 签名工具链 |
| HMDFS 权限限制 | TMPDIR=/data/storage/el2/base/cache |

## 质量门禁

- G1-G4: PASS

---

**编译结束**: 2026-06-08
**状态**: published
