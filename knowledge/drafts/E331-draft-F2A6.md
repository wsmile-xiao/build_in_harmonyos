# E331: Go 链接器 fallocate 在 OHOS HMDFS 上失败

> **结构化数据**: [draft/E331-draft-F2A6.kv](../draft/E331-draft-F2A6.kv) | **原则**: P-TOOLCHAIN-001
> **严重度**: 🔴 blocking | **分类**: toolchain | **自动修复**: ❌ manual

---

## 错误特征

```
# command-line-arguments
/storage/Users/currentUser/usr/local/go/pkg/tool/linux_arm64/link: mapping output file failed: permission denied
```

## 根因

Go 链接器 (`cmd/link`) 在写入输出文件时调用 `fallocate()` 系统调用预分配文件空间。
OHOS 的 HMDFS 和 tmpfs 文件系统不支持 `fallocate()`，返回 `EACCES` (errno=13, Permission denied)。

Go 链接器的源码 (`outbuf_mmap.go`) 中，`fallocate` 错误只忽略 `ENOTSUP`、`EPERM` 和 `errNoFallocate`，
不忽略 `EACCES`，导致错误被传播为致命错误。

关键代码位置: `GOROOT/src/cmd/link/internal/ld/outbuf_mmap.go` 第 31 行:
```go
if err != syscall.ENOTSUP && err != syscall.EPERM && err != errNoFallocate {
    return err  // EACCES 在这里被返回
}
```

## 受影响范围

所有在 OHOS 上使用 Go 工具链编译的 Go 项目。包括 `go build`、`go install`、`go test` 等。

## 解决方案（推荐）

### 方案 1: toolexec 包装器（推荐）

创建一个 shell 脚本作为 `go build -toolexec` 的包装器，拦截链接工具调用，
将输出重定向到 `/dev/shm`（支持 fallocate），链接完成后再复制回原路径。

```bash
# 创建包装器脚本
cat > $HOME/tmp/toolexec_wrapper.sh << 'WRAPPER'
#!/storage/Users/currentUser/usr/local/bin/bash
tool="$1"
shift
if [[ "$tool" == *"/link" ]]; then
    args=("$@")
    output_path=""
    for i in "${!args[@]}"; do
        if [[ "${args[$i]}" == "-o" ]]; then
            output_path="${args[$((i+1))]}"
            args[$((i+1))]="/dev/shm/go_link_output_$$"
            break
        fi
    done
    tmp_output="/dev/shm/go_link_output_$$"
    rm -f "$tmp_output"
    "$tool" "${args[@]}"
    ret=$?
    if [ $ret -eq 0 ] && [ -f "$tmp_output" ]; then
        cp "$tmp_output" "$output_path"
        rm -f "$tmp_output"
    fi
    exit $ret
else
    exec "$tool" "$@"
fi
WRAPPER
chmod +x $HOME/tmp/toolexec_wrapper.sh

# 使用包装器编译
go build -toolexec $HOME/tmp/toolexec_wrapper.sh -o myapp ./cmd/myapp/
```

### 方案 2: 修改 Go 源码（回退）

修改 `GOROOT/src/cmd/link/internal/ld/outbuf_mmap.go`，在 fallocate 错误忽略列表中添加 `syscall.EACCES`。
但此方案需要重建 Go 链接器，而重建过程本身也需要链接器（鸡生蛋问题）。

## 验证命令

```bash
# 测试 fallocate 是否在当前文件系统上失败
cat > /tmp/falloc_test.c << 'EOF'
#include <fcntl.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
int main() {
    int fd = open("/tmp/test_falloc", O_CREAT|O_RDWR, 0775);
    int ret = fallocate(fd, 0, 0, 4096);
    printf("fallocate: ret=%d errno=%d (%s)\n", ret, errno, strerror(errno));
    return 0;
}
EOF
clang -o /tmp/falloc_test /tmp/falloc_test.c && /tmp/falloc_test
# 如果输出 "fallocate: ret=-1 errno=13 (Permission denied)" 则确认此问题
```

## 涉及软件

所有 Go 项目在 OHOS 上编译时。

## 相关模式

- E002 — /tmp 只读（同为文件系统限制类）

## 注意事项

1. `/dev/shm` 在 OHOS 上可以创建文件但不能创建目录，所以包装器直接使用文件名
2. toolexec 包装器的 shebang 必须指向 OHOS 上的 bash 路径（`/storage/Users/currentUser/usr/local/bin/bash`）
3. Go 工具链内部工具（compile, link, asm 等）也需要签名才能在 OHOS 上执行
4. LD_PRELOAD 方案无效，因为 Go 直接使用系统调用而非 libc

---
*doc/E331.md · knowledge graph draft · 2026-07-02 · contributor: F2A6*
