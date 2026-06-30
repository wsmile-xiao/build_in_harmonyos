# Jigdo

## 简介

Jigdo (Jigsaw Download) 是一个用于高效下载大型文件（如 Debian CD/DVD 映像）的工具。它通过下载单个文件并将它们重新组装成完整的映像来工作，避免了下载整个 ISO 映像的需要。

主要组件：
- **jigdo-file**: 主程序，用于生成和下载 jigdo 文件
- **jigdo-lite**: 轻量级下载脚本，简化下载流程
- **jigdo-mirror**: 用于镜像维护的工具

## OHOS 适配

- 使用 autotools 构建系统，支持标准的 configure/make 流程
- libdb 功能可选（用于文件缓存），无预编译包时使用 `--without-libdb` 禁用
- GUI 功能可选，使用 `--without-gui` 禁用
- HMDFS 文件系统限制：configure 阶段 config.status 创建临时子目录会失败，需手动处理
- 文档生成依赖 docbook2man，缺失时可跳过，只编译二进制文件

## 依赖

- **bzip2**: 编译依赖（必需）
- **wget**: 运行时依赖（jigdo-lite 和 jigdo-mirror 脚本需要）
- **libdb**: 可选（已禁用）

## 功能验证

```bash
jigdo-file --version
jigdo-lite --help
```

## 注意事项

- libdb 功能已禁用，db 文件缓存不可用（性能略降）
- 无 man 页面，从 README 获取使用说明
- jigdo-lite 和 jigdo-mirror 脚本依赖 wget（需确保 wget 可用）

## 参考

- 官网: https://www.einval.com/~steve/jigdo/ (可能无法访问)
- Debian: https://packages.debian.org/jigdo
- 源码: https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/j/jigdo/