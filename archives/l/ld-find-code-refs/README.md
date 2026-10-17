# ld-find-code-refs

ld-find-code-refs 是 LaunchDarkly 官方的命令行工具（纯 Go）：扫描代码库中的 feature flag 引用，把结果上报到 LaunchDarkly 平台，供 code references / 分支 extinction 追踪使用。

- 上游仓库：https://github.com/launchdarkly/ld-find-code-refs
- 许可证：Apache-2.0
- 语言：Go（CGO_ENABLED=0，纯静态）
- 适配路径：路径 A（基础适配）

## 版本

| 版本 | 状态 | 构建日期 |
|------|------|----------|
| 2.14.0 | built | 2026-09-26 |

## 用法

```bash
ld-find-code-refs --version                  # 打印版本并退出
ld-find-code-refs --help                     # 打印用法
ld-find-code-refs                            # 按 ld-find-code-refs.yml 配置扫描并上报
ld-find-code-refs prune "branch1" "branch2"  # 清理指定分支的 code reference 数据
ld-find-code-refs extinctions                # 查询分支的 extinction 记录
```

运行需要仓库内提供访问令牌（`accessToken`，配置文件或环境变量）与 git>=2.21。

## OHOS 适配要点

- 纯 Go 应用，无 C/C++ 目标库；上游自带完整 vendor/，-mod=vendor 离线构建+测试（GOPROXY=off）
- Go 工具链与最终产物均需 binary-sign-tool 自签（OHOS Seccomp 拦截未签名 ELF）
- Go 缓存/链接输出/测试工作目录放在非 hmfs 工作区（E051/E166 经验）
- 版本号为 internal/version 包中的 Go 常量，随源码烘焙（2.14.0），无需 ldflags -X
- 上游 `go test -mod=vendor ./...` 共 11 文件/9 包/35 个顶层测试函数（含 90 个子用例）在 OHOS 上全部通过（-exec 自签 wrapper）
