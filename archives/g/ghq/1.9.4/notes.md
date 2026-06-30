# ghq 1.9.4 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-01
- 编译器: Go 1.26.2 (CGO_ENABLED=0)
- 状态: published

## 编译步骤

1. 下载并解压 ghq v1.9.4 源码到 ~/tmp/builds/ghq-1.9.4.work/
2. 签名 Go 1.26.2 工具链二进制（pkg/tool/linux_arm64/）以允许执行
3. 设置环境变量:
   - GOROOT=~/tmp/go1.26.2-extract/go
   - GOTOOLCHAIN=local
   - GOPROXY=https://goproxy.cn,direct
   - CGO_ENABLED=0
   - TMPDIR=~/tmp
4. 构建命令: `go build -ldflags="-s -w" -o ghq .`
5. **关键**: 构建输出必须指向 hmfs 文件系统（/data/storage/el2/base/cache/），而非 HMDFS，因为 Go linker 需要 mmap 支持
6. ELF 签名 ghq 二进制: `ohc-run.py sign-elf`
7. 安装到 TEST_PREFIX 和 DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go linker "mapping output file failed: permission denied" | HMDFS 不支持 mmap 写操作 | 构建输出到 hmfs (/data/storage/el2/base/cache/) |
| 2 | Go 1.26.0 runtime source has duplicate declarations | Go 1.26.0 安装损坏（traceexp.go vs tracebuf.go, strconv/number.go等） | 使用 Go 1.26.2 tarball |
| 3 | Go tool binaries permission denied | pkg/tool/linux_arm64/* 未 ELF 签名 | ohc-run.py sign-elf --batch 签名8个工具 |
| 4 | Songmu/gitconfig requires Go >= 1.25.0 | 依赖版本要求 | 必须使用 Go 1.26.x，不能用 Go 1.22 |
| 5 | binary-sign-tool 对 Go 二进制失败 | Go ELF 格式无 .codesign section 空间 | 使用 ohc-run.py sign-elf 批量签名 |

## 依赖版本

- Go 1.26.2 (linux/arm64)
- GOPROXY 下载的 Go 模块依赖（见 go.sum）

## 验证结果

```bash
$ ~/usr/local/bin/ghq --version
ghq version 1.9.4 (rev:HEAD)
```

## 注意事项

- Go 项目编译需要在 hmfs 文件系统上进行（HMDFS 不支持 linker mmap）
- Go 工具链二进制需要 ELF 签名才能执行
- Go 1.26.0 本地安装有源码损坏问题，需使用 1.26.2
---

**编译结束**: 2026-06-01 17:24
**最终状态**: published
