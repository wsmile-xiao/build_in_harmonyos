# mockery v2.46.0 编译笔记

## 编译信息
- 软件: mockery (Go mock generator)
- 版本: v2.46.0
- 构建系统: Go (custom)
- 来源: Homebrew (下载量3148)
- 项目URL: https://github.com/vektra/mockery

## 编译过程

### 1. 源码获取
- GitHub下载超时，使用Go模块代理(goproxy.cn)获取源码
- 从Go模块缓存(`~/go/pkg/mod/github.com/vektra/mockery/v2@v2.46.0`)复制到构建目录

### 2. 依赖处理
- 原始依赖 golang.org/x/tools@v0.17.0 与 Go 1.26.3 不兼容
- tokeninternal.go 中 `-delta * delta` 导致编译错误
- 解决: `go get golang.org/x/tools@latest` 升级到 v0.45.0
- 同时升级 golang.org/x/mod v0.14.0 → v0.36.0, golang.org/x/sys v0.6.0 → v0.44.0

### 3. 构建命令
```bash
CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct \
~/usr/local/go1263/bin/go build \
-ldflags "-X github.com/vektra/mockery/v2/pkg/logging.SemVer=v2.46.0 -s -w" \
-o $DESTDIR/bin/mockery .
```

### 4. 平台适配
- **Go -s -w strip**: 使用Go内置strip，不使用llvm-objcopy（后者会破坏Go二进制）
- **patchelf RPATH**: 禁止使用（会破坏Go ELF结构导致SIGSEGV）
- mockery仅依赖libc.so（系统库），无需设置RPATH
- **ELF签名**: 必须签名才能在HarmonyOS上执行，签名前报permission denied

### 5. 验证
```
$ ~/usr/local/bin/mockery --version
v2.46.0
```

## 关键发现（知识沉淀）
1. **Go二进制不可用patchelf**: patchelf修改Go ELF会破坏`.go.buildinfo`等特殊段，导致SIGSEGV
2. **Go二进制不可用llvm-objcopy --strip-debug**: 会移除Go运行时必需的段
3. **Go strip应使用-ldflags "-s -w"**: Go自身知道哪些段可以安全移除
4. **golang.org/x/tools版本兼容性**: v0.17.0不兼容Go 1.26+，需升级到v0.45.0+
5. **版本注入**: Go项目用 `-X pkg.Var=value` ldflags注入版本到全局变量

**编译开始**: 2026-06-02 03:29 UTC
**编译结束**: 2026-06-02 03:55 UTC
**最终状态**: published
---

**编译结束**: 2026-06-02 11:58
**最终状态**: built
