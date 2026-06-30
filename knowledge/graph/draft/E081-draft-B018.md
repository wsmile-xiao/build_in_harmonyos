# E081 — Go link 工具输出文件映射权限问题

## 错误特征
编译 Go 项目时，Go link 工具在尝试映射输出文件到内存时报错：
```
/storage/Users/currentUser/usr/local/go/pkg/tool/linux_arm64/link: mapping output file failed: permission denied
```

此错误发生在 `go build` 的链接阶段，导致无法生成最终的可执行文件。

## 触发条件
- 构建系统: Go（Go 1.25 及更高版本）
- 阶段: linking（链接）
- 环境: 鸿蒙系统（SELinux 或安全策略限制）

## 根因分析
Go link 工具在链接过程中使用 mmap 将输出文件映射到内存以提高性能。在鸿蒙系统上，SELinux 或其他安全策略可能阻止 mmap 操作，导致权限错误。

这是 Go 1.25+ 版本的特定问题，可能是因为：
1. Go 1.25 引入了新的链接器优化
2. 鸿蒙系统的安全策略更严格
3. mmap 权限未被正确配置

## 解决方案

### 推荐方案
**启用 CGO，使用系统链接器替代 Go link 工具**

CGO_ENABLED=1 时，Go 会使用系统的链接器（clang/gcc 的 ld）而不是 Go 自带的 link 工具，从而绕过 mmap 权限问题。

步骤：
1. 安装必要的 C 库依赖（如 libpcsclite）
2. 设置环境变量：`export CGO_ENABLED=1`
3. 设置编译器：`export CC=clang`
4. 编译：`go build -v -o bin/${NAME} ${PKG}`

### 替代方案
如果无法使用 CGO（如缺少 C 库依赖），可以：
1. 尝试使用较低版本的 Go（如 Go 1.22）
2. 降低项目依赖包的版本以兼容较低的 Go 版本

### 禁止做法
- ❌ 不要尝试修改 SELinux 策略（可能导致系统安全问题）
- ❌ 不要使用 chmod 修改 link 工具权限（无效）
- ❌ 不要尝试在 /tmp 目录输出（同样的权限问题）

## 验证
```bash
# 测试 CGO 编译是否成功
export CGO_ENABLED=1 && export CC=clang && go build -v -o bin/test ${PKG}
ls -la bin/test
```

## 关联条目
- 相关: Go 版本依赖冲突（Go >= 1.25 要求）
- 相关: CGO 编译缺少 C 库依赖
