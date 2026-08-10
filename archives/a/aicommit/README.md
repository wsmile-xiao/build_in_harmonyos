# aicommit

aicommit 是生成 git commit message 的命令行小工具，会遵循仓库既有的提交风格（读取仓库根目录 COMMITS.md，或用户级 ~/COMMITS.md）。

- 上游仓库：https://github.com/coder/aicommit
- 许可证：CC0-1.0
- 语言：Go（CGO_ENABLED=0，纯静态）
- 适配路径：路径 A（基础适配）

## 版本

| 版本 | 状态 | 构建日期 |
|------|------|----------|
| 0.6.5 | built | 2026-08-10 |

## 用法

```bash
export OPENAI_API_KEY="..."
aicommit            # 为暂存区变更生成提交信息
aicommit -d         # 干跑，只输出信息不提交
aicommit -c "closes #123"   # 附带上下文
aicommit version    # 输出版本
```

## OHOS 适配要点

- Go 工具链与产物均需 binary-sign-tool 签名（Seccomp 拦截未签名 ELF）
- Go linker 链接输出必须放到非 hmdfs 工作区
