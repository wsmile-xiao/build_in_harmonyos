# esbuild 0.25.12 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-08-06
- 编译器: go 1.26.5 (Harmonybrew)
- 状态: built

## 编译步骤

1. 安装 Go 1.26.5 via Harmonybrew (`brew install go`)
2. 设置 GOPROXY=https://goproxy.cn,direct (中国镜像)
3. 构建 seccomp BPF wrapper 拦截 fallocate 系统调用
4. 执行 `CGO_ENABLED=0 go build -toolexec seccomp_wrap -ldflags="-s -w" -trimpath ./cmd/esbuild`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go linker "mapping output file failed: permission denied" | HarmonyOS 的 fallocate 系统调用返回 EACCES，Go linker 未将 EACCES 列入可忽略错误 | 构建 seccomp BPF wrapper 拦截 fallocate (syscall #47 on OHOS) 并返回 EOPNOTSUPP，使 Go linker 回退到 Truncate+Mmap 路径 |
| 2 | HMDFS 硬链接失败 | init-build 的 shutil.copytree(copy_function=os.link) 在 HMDFS 上失败 | 手动用 `cp -rL` 创建 work 目录 |
| 3 | Go proxy 超时 | proxy.golang.org 不可达 | 使用中国镜像 goproxy.cn |

## 源码修改

无源码修改，通过 seccomp wrapper 解决平台兼容性问题。

## 依赖版本

- Go 1.26.5 (Harmonybrew)
- golang.org/x/sys v0.0.0-20220715151400-c0bba94af5f8

## 验证结果

```bash
$ esbuild --version
0.25.12
```

## 注意事项

- Go linker 的 fallocate 系统调用在 HarmonyOS 上返回 EACCES (syscall #47)
- 标准 Linux 使用 syscall #285，HarmonyOS 使用 #47 (asm-generic 编号)
- seccomp wrapper 同时拦截 #47 和 #285 以兼容两种环境
---

**编译结束**: 2026-08-06 09:47
**最终状态**: built
