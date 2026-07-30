# ydiff 1.5 适配笔记

## 编译环境

- 构建系统: custom（纯 Python 单文件 CLI）
- 编译日期: 2026-07-27
- 编译器: 不适用
- 状态: built

## 编译与安装

ydiff 1.5 仅依赖 Python 3.3 及以上版本的标准库。配方下载并校验上游 1.5 tag 完整源码 tarball，执行 Python 字节码语法检查和版本检查，然后将 `ydiff.py` 安装为 `bin/ydiff` 并设置执行权限。

## 上游测试

上游 1.5 tag tarball 包含 55 个 Python unittest 测试和 144 个回归输出比较，共 199 个检查项。配方使用的 tarball 携带完整测试目录；上游完整测试套件在源码验证阶段执行（Windows 环境下 5 个依赖 `/bin/sh` 的测试因宿主限制跳过，OHOS 环境下全部通过），消费者阶段补充验证 Conan 包内命令的核心功能。

## 源码修改

无源码修改，无补丁。

## 依赖版本

无 Conan 依赖。运行时需要 Python 3.3 或更高版本；可选 pager `less` 不影响非交互和 `--pager=cat` 场景。

## 消费者验证

| 检查 | 预期结果 |
|------|----------|
| `ydiff --version` | 输出 `ydiff 1.5` |
| 统一模式 stdin diff | 保留统一差异内容且退出码为 0 |
| 并排模式 stdin diff | 输出新旧内容和行号且退出码为 0 |
