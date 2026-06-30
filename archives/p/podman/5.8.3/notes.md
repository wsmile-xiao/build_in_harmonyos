# podman 5.8.3 — 适配笔记

## 平台
- 目标: OpenHarmony (aarch64, musl libc)
- Go: 1.26.4 (HarmonyBrew)
- C编译器: ohos-sdk clang

## 关键适配

### 1. Go工具链
使用 HarmonyBrew 安装的 Go: `brew install go ohos-sdk llvm-gcc-compat`
- binary-sign-tool 自动对编译产物签名
- cc 命令由 llvm-gcc-compat 提供 (指向 ohos-sdk clang)

### 2. CGO编译方案
HarmonyOS 安全策略阻止 Go 链接器对输出文件 mmap，解决方案：
- 编译参数: `-ldflags=-linkmode=internal` (使用Go内部链接器)
- 构建模式: 默认 (不使用 `-buildmode=pie`，PIE + internal 导致段错误)

### 3. sqlite3 纯 Go 替代
将 CGO 版本的 go-sqlite3 替换为纯 Go 存根驱动
- 原因: go-sqlite3 的 C 代码产生 internal linker 无法处理的 R_AARCH64_ABS64 重定位
- 方式: 创建 `database/sql` 兼容的纯 Go 驱动
- 限制: sqlite 功能不可用 (podman 默认用 sqlite 数据库后端)

### 4. pthread 兼容性
- `pthread_mutex_consistent` / `pthread_mutexattr_setrobust`: HarmonyOS musl 不提供
- 修复: 在 shm_lock.c 中添加兼容内联函数

### 5. 编译命令
```
CGO_ENABLED=1 GOOS=linux GOARCH=arm64 \
  go build \
    -tags "containers_image_openpgp seccomp exclude_graphdriver_btrfs" \
    -ldflags="-linkmode=internal ..." \
    -o bin/podman ./cmd/podman
```

### 6. 产物
- bin/podman (59MB ELF, signed by binary-sign-tool)
- 在 HarmonyOS 上可执行，但存储后端因 sqlite 存根需要额外配置
