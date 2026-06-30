# foremost

基于文件头和尾进行取证数据恢复的工具。

- **许可证**: 公共领域（Public Domain）
- **语言**: C
- **构建系统**: Makefile（无 configure 脚本）
- **版本**: 1.5.7
- **源码**: https://foremost.sourceforge.net/

## 简介

Foremost 是一个取证数据恢复工具，最初由美国空军特别调查办公室开发。
它通过文件雕刻（carving）方式，根据文件的头部签名、尾部签名和内部数据结构
来从磁盘映像或原始数据中恢复被删除或损坏的文件。

支持的文件类型包括：JPEG、GIF、PNG、BMP、AVI、PDF、DOC、MPG、WMV 等，
用户也可通过配置文件自定义要搜索的文件类型签名。

## 鸿蒙构建说明

- 鸿蒙系统 `uname -s` 返回 "HarmonyOS"，需要在 Makefile 中将 SYS 映射到 "linux"
- 头文件中全局变量定义未加 `extern` 导致 clang/lld 出现 duplicate symbol 错误（E105）
- 需要在头文件中添加 extern 声明，在 main.c 中添加实际定义
- Makefile 需添加 PREFIX 和 DESTDIR 支持以适配安装路径

## 用法示例

```bash
# 恢复 JPEG 和 GIF 文件
foremost -t jpeg,gif -i disk_image.bin -o output/

# 使用自定义配置文件
foremost -c foremost.conf -i disk_image.bin -o output/

# 仅审计模式（不写入文件到磁盘）
foremost -w -i disk_image.bin -o output/

# 快速模式（512 字节边界搜索）
foremost -q -t jpeg -i disk_image.bin -o output/
```