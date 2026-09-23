# pcal

## 简介

pcal 是一个命令行日历生成工具，可以输出月历或年历的 PostScript、HTML，以及传统 calendar 格式文本。上游 4.11.0 版本使用纯 C 源码和顶层 Makefile 构建。

## 构建系统

- 类型: Makefile
- 主要命令: `make`
- 输出程序: `pcal`
- 外部运行时依赖: 无

## OHOS 适配要点

1. 上游 Makefile 默认使用 `/usr/bin/gcc`，在 OHOS 上需要通过 `CC=clang` 显式覆盖。
2. 上游安装目标会生成 man/cat 文档并调用 `nroff`、`groff`、`compress` 等可选工具；Conan recipe 只执行核心编译，并手动打包已生成的二进制和手册源文件。
3. GNU make 在当前用户目录的 `$TMPDIR` 上创建 jobserver FIFO 会失败，因此 recipe 固定使用 `make -j1`。
4. pcal 是命令行工具，不导出库；`package_info()` 仅暴露 `bin`，软件级目录声明 `commands.json`。

## 功能验证

```bash
pcal -v
pcal -e 9 2026
pcal -H -e 9 2026
pcal -c 9 2026
```

## 许可证

源码文档声明原始 PostScript 日历代码获得修改和再分发许可；项目未提供标准 SPDX 许可证文件，recipe 使用 `custom-permissive` 标记。

## 参考

- 官网: https://pcal.sourceforge.net
- 源码: https://downloads.sourceforge.net/project/pcal/pcal/pcal-4.11.0/pcal-4.11.0.tgz
