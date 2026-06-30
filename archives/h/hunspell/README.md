# Hunspell

## 简介

Hunspell 是一个开源的拼写检查库和命令行工具，源自 MySpell，被 LibreOffice、Mozilla Firefox、Google Chrome 等众多项目使用。支持复杂的词法分析、多语言词典和自定义词典格式。

## OHOS 适配

### 平台检测修复

- **E007**: config.guess 需添加 `*:HarmonyOS:*:*` case 分支，输出 `aarch64-unknown-linux-ohos` 三元组
- **E072**: config.sub 需在三处添加 ohos 支持：
  - maybe_os 列表添加 `linux-ohos*`
  - 添加 `-ohos*` 处理分支
  - kernel-os 白名单添加 `linux-ohos*`

### HMDFS 文件系统限制

- 临时目录问题：`umask 077 && mktemp` 创建的目录带有 setgid 位（2700权限），导致无法创建临时文件
  - 解决：修改 configure，移除 `umask 077`，使用 `${TMPDIR:-$HOME/tmp}` 作为临时目录
- 符号链接问题：动态链接器无法正确解析 HMDFS 上的符号链接库文件
  - 解决：将 `.so` 符号链接替换为实际库文件副本（`cp -a`）

## 依赖

无外部编译依赖（自包含构建）。

## 功能验证

```bash
hunspell --version
# 输出：Hunspell 1.7.2

# 基本拼写检查
echo "hello world" | hunspell
```

## 参考

- 官网: https://hunspell.github.io
- 源码: https://github.com/hunspell/hunspell
- 词典: https://github.com/hunspell/hunspell-dictionaries