# lha (LHa for UNIX)

## 简介
lha 是 LHarc/LHa 格式的压缩/解压工具，常见于日本计算环境。

## OHOS 适配
- 项目缺少 configure 脚本，需手动创建 Makefile 和 config.h
- 需要添加 libgen.h 和 iconv.h 兼容性头文件
- 6个补丁文件：添加 config.h、configure脚本、Makefile、修复头文件和 UTF-8 支持
- `hints/build.sh` 包含完整构建脚本

## 依赖
- libiconv（可选，用于 UTF-8 支持）

## 功能验证
```bash
lha --version
```

## 注意事项
- 所有已知下载源不稳定（GitHub 超时、OSDN SSL 证书问题）
- 建议保留本地源码副本

## 参考
- 主页: https://github.com/jca02266/lha
