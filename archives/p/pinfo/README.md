# Przemek's Info Viewer (pinfo)

> Info 文件查看器，提供比 GNU info 更友好的用户界面

## 简介

pinfo 是一个 Info 文件查看器，用于阅读 GNU Info 格式的文档。它提供了比传统 GNU info 命令更友好的用户界面，支持颜色显示、键盘导航和链接跳转。

pinfo 最初由 Przemek Borys 开发，现在由社区维护。它是一个轻量级的文档查看工具，特别适合在没有图形界面的环境中阅读 Info 文档。

## OHOS 适配要点

在 HarmonyOS 上编译和使用 pinfo 时需要注意：

1. **Bootstrap 项目**：原始 tarball 中不包含 configure 脚本，需要运行 `autoreconf -i` 生成
2. **clean_verify.py 支持**：编译框架已支持 autoreconf（2026-06-15），无需手动生成
3. **HMDFS 限制**：在 HMDFS 文件系统上，config.status 可能因临时文件限制而失败；在其他环境（标准 Linux）应可正常编译
4. **依赖项**：需要 ncurses 和 gettext（autopoint）

## 排除与替代

无需排除的组件。pinfo 本身是独立可执行文件。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 6.4+ | 终端界面库 |
| gettext | 0.22+ | 国际化工具（提供 autopoint） |

## 功能验证

```bash
# 查看版本
pinfo --version

# 查看 Info 文档（示例）
pinfo pinfo

# 查看帮助
pinfo --help
```

## 参考

- [GitHub 仓库](https://github.com/baszoetekouw/pinfo)
- [Debian 软件包](https://packages.debian.org/pinfo)
- [Info 文档格式](https://www.gnu.org/software/texinfo/manual/info/)