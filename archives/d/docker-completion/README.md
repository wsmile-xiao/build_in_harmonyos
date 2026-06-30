# docker-completion

## 简介

docker-completion 是 Docker CLI 的 bash 自动补全脚本，为 docker 命令提供 Tab 键补全功能。此软件为纯文本 bash 脚本，无需编译，直接复制安装即可。

## OHOS 适配

### 适配要点

1. **无编译流程**：docker-completion 是纯 bash 脚本，不需要 configure/make 等传统编译步骤
2. **安装路径**：安装到 `$PREFIX/share/bash-completion/completions/docker`
3. **依赖 bash-completion**：需要先安装 bash-completion 包才能生效
4. **SSL 证书问题**：HarmonyOS 缺少 CA 证书时，可使用 toybox wget 下载（自动跳过 SSL 验证）

### 已知问题

- 源码来自 Docker CLI 仓库，包含 Go 代码，但 completion 脚本是纯 bash，无需 Go 环境

## 排除与替代

无排除组件（仅包含一个 completion 脚本）

## 依赖

### 运行依赖

| 依赖 | 说明 |
|------|------|
| bash-completion | 提供 bash 补全框架 |

### 编译依赖

无编译依赖（纯文本脚本）

## 功能验证

```bash
# 检查安装
ls -la $PREFIX/share/bash-completion/completions/docker
file $PREFIX/share/bash-completion/completions/docker
# 输出: bash script

# 在 .bashrc 中启用
source $PREFIX/share/bash-completion/completions/docker

# 测试补全
docker <Tab><Tab>
# 应显示 docker 子命令列表
```

## 参考

- 官方仓库: https://github.com/docker/cli
- 补全脚本路径: contrib/completion/bash/docker
- 许可证: Apache-2.0