# kubelogin 1.36.2 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-01
- 编译器: Go 1.26.2 (clang backend)
- 状态: published

## 编译步骤

kubelogin 是 Go 语言编写的 kubectl OIDC 认证插件，使用 Go build 系统而非 autotools。

1. 下载源码：从 GitHub kubelogin v1.36.2 获取
2. 使用 Go 编译：`CGO_ENABLED=1 GOOS=linux GOARCH=arm64 go build -o kubectl-oidc_login`
3. ELF 签名：`binary-sign-tool sign -inFile kubectl-oidc_login -outFile /tmp/signed -selfSign 1` → rm + cp 替换（避免 HMDFS 签名回退）
4. 安装到 staging 目录和 ~/usr/local/bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS shutil.move 签名回退 | HMDFS 特有行为 | 使用 rm+cp 方式替换签名文件 |
| 2 | /tmp 不可写 | OpenHarmony /tmp 只读 | 设置 TMPDIR=/data/storage/el2/base/cache |
| 3 | verify-build G4 缺少 build_system | manifest 模板用嵌套 build.system | 添加顶层 build_system: custom |

## 源码修改

- `go.mod`: 修改 Go 版本依赖（补丁 0001-go.mod.patch）

## 依赖版本

- Go 1.26.2

## 验证结果

```bash
$ kubectl-oidc_login --version
kubelogin version 1.36.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| kubelogin-1.36.2-ohos-aarch64.tar.gz | 14282KB | 预编译包 |
| kubelogin-1.36.2-ohos-aarch64-debug.tar.gz | 77KB | 调试符号包 |
| 0001-go.mod.patch | 1 file, +0/-5 | Go 版本适配补丁 |

## 注意事项

- Go 项目使用 custom 构建系统，不是 autotools
- 签名文件必须使用 rm+cp 替换，不能用 shutil.move
---

**编译结束**: 2026-06-01 18:24
**最终状态**: published
