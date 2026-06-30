# bchunk

> BinChunker converts CD images in .bin/.cue format to .iso/.cdr tracks

## 简介

bchunk (BinChunker) 是一个用于转换 CD-ROM 镜像格式的小型工具。它可以将 .bin/.cue 格式的光盘镜像转换为 .iso 和 .cdr 音轨文件。

该工具主要用于处理通过 cdrdao 或类似工具创建的 .bin/.cue 格式的 CD 镜像，使其可以转换为更通用的 .iso 格式或提取音轨。

## OHOS 适配要点

- OpenHarmony 系统缺少 `install` 命令，Makefile 需要修改为使用 `cp` + `chmod` 替代
- 使用 clang 编译器替代 gcc
- 支持 DESTDIR 安装模式
- 支持 PREFIX 环境变量指定安装路径

## 排除与替代

无特殊排除项。该工具为独立命令行程序，无可选组件。

## 依赖

无外部依赖。bchunk 是纯 C 程序，仅依赖标准 C 库。

## 功能验证

```bash
# 显示版本信息
bchunk

# 转换示例（需要准备 .bin/.cue 文件）
bchunk foo.bin foo.cue foo
```

## 参考

- [官方网站](http://he.fi/bchunk/)
- [源码下载](http://he.fi/bchunk/bchunk-1.2.2.tar.gz)