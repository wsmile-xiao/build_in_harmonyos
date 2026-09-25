# infgen — DEFLATE 流反汇编工具

## 简介

infgen 是 zlib 作者 Mark Adler 编写的单文件 C 命令行工具，用于读取 gzip、zlib、PNG 或 raw deflate 压缩流，并输出可读的位级描述。可用于学习 deflate 压缩格式、分析压缩数据、调试 deflate 压缩器。

## 已适配版本

- **版本**: 3.5（上游无 git tag，对应 commit `c6fe0c3`）
- **状态**: built（前置适配完成，待真机 shadow CI）
- **许可证**: zlib（SPDX: Zlib）
- **构建系统**: custom（无 Makefile/configure，直接 clang 编译单文件）
- **依赖**: zlib/1.3.1（静态链接，PNG 输入 CRC 校验用）

## 下载地址

- 源码: https://github.com/madler/infgen/archive/c6fe0c3.tar.gz
- 上游仓库: https://github.com/madler/infgen

## 用法示例

```bash
# 查看帮助与版本
infgen -h

# 反汇编一个 gzip 文件
infgen < foo.gz > foo.def

# 直接指定输入文件
infgen foo.gz > foo.def

# 显示原始动态块头信息
infgen -d < foo.gz

# 二进制输出格式
infgen -b < foo.gz
```

## 注意事项

- infgen 从 stdin 读取压缩流，描述写入 stdout
- PNG 输入需要链接 zlib（`crc32`），本适配静态内嵌 zlib
- HarmonyOS 上可执行文件需 `binary-sign-tool` 签名后方可运行
