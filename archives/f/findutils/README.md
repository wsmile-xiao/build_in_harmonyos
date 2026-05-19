# GNU findutils

## 简介
GNU findutils 是 GNU 项目提供的文件查找工具集，包含以下核心组件：
- **find**: 递归搜索文件系统，查找符合指定条件的文件
- **xargs**: 从标准输入构建并执行命令行
- **locate**: 快速文件名查找工具（依赖数据库）
- **updatedb**: 更新 locate 数据库

## 编译版本
- 版本: 4.10.0
- 状态: built
- 编译系统: autotools

## 功能特点
- 丰富的搜索条件（文件名、类型、大小、时间等）
- 支持正则表达式匹配
- 可与其他 GNU 工具无缝集成
- 高效的文件系统遍历算法

## 使用方法
```bash
# 查找所有 .txt 文件
find /path -name "*.txt"

# 查找最近 7 天修改的文件
find /path -mtime -7

# 查找并执行操作
find /path -name "*.log" -exec rm {} \;

# 使用 xargs 处理大量文件
find /path -type f | xargs chmod 644
```

## 链接
- 官方网站: https://www.gnu.org/software/findutils/
- 源码下载: https://ftp.gnu.org/gnu/findutils/