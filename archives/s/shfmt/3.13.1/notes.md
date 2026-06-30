# shfmt 3.13.1 适配笔记

## 编译环境
- 构建系统: go (CGO_ENABLED=0)
- 编译日期: 2026-06-14
- 编译器: clang/clang++ (Go 不使用)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build shfmt 3.13.1 --url=https://github.com/mvdan/sh/archive/refs/tags/v3.13.1.tar.gz`
2. `source .build-context-shfmt-3.13.1`
3. `cd $BUILD_SRC_DIR && CGO_ENABLED=0 GOPROXY=https://goproxy.cn,direct GOTOOLCHAIN=local go build -o shfmt ./cmd/shfmt`
4. 安装到 staging 和本地

## 遇到的问题与解决方案

无特殊问题，纯 Go 项目 CGO_ENABLED=0 编译成功

## 源码修改

无源码补丁

## 依赖版本

- Go: 1.25.x (via goenv 3.1.1)

## 验证结果

```bash
shfmt --version
3.13.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| shfmt-3.13.1-ohos-aarch64.tar.gz | ~5MB | Release包 |
| shfmt-3.13.1-ohos-aarch64-debug.tar.gz | ~5MB | Debug包 |

## 注意事项

- shfmt 是纯 Go 项目，CGO_ENABLED=0 编译
- 需要 ELF 签名
---
**编译结束**: 2026-06-14 00:02
**最终状态**: built
