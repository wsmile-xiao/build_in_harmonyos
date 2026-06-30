# shfmt

> shfmt — Shell 格式化工具

## 简介

shfmt 是一个 shell parser、formatter 和 interpreter。它支持 POSIX shell、bash 和 mksh 格式化。shfmt 也可用于检查 shell 脚本的格式问题。

## OHOS 适配要点

- 纯 Go 项目，CGO_ENABLED=0 编译
- 使用 goenv 管理的 Go 版本
- 需要 ELF 签名才能在 HarmonyOS 上执行

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| goenv | 3.1.1 | Go 版本管理 |

## 功能验证

```bash
shfmt --version
```

## 参考

- [官方文档](https://github.com/mvdan/sh)
- [源码仓库](https://github.com/mvdan/sh)
