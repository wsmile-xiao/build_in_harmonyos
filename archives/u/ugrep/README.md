# ugrep

## 简介

ugrep 是一个超快速文件搜索工具，是 grep 的现代化替代品。它支持：
- 超快速搜索（比 grep 快 3-10 倍）
- 递归搜索目录
- 正则表达式匹配
- 多种压缩文件格式（.gz, .bz2, .xz, .lzma, .lz4, .zst, .br）
- 7zip 文件搜索
- 彩色输出
- 交互式查询模式

## 编译状态

| 版本 | 状态 | 构建系统 | 补丁数 |
|------|------|----------|--------|
| 7.8.2 | ✅ 已发布 | autotools | 2 |

## 详细版本信息

- **7.8.2**: [查看详情](7.8.2/)

## 编译要点

1. **HarmonyOS 平台适配**：需要应用 config.guess 和 config.sub 补丁以正确识别系统类型
2. **HMDFS 文件系统限制**：需要特殊处理临时文件创建（详见 hints/README-hmdfs.md）
3. **依赖库**：需要 zlib，可选依赖包括 pcre2、bz2、lzma、lz4、zstd、brotli

## 参考链接

- 官网：https://ugrep.com/
- GitHub：https://github.com/Genivia/ugrep
- 文档：https://ugrep.com/manual.html