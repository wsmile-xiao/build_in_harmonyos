# Command Line Progress Bar — OpenHarmony 编译档案

## 软件简介
clpbar（`bar`）是一个命令行进度条工具：把输入数据流复制到输出，
同时在 stderr 显示传输量、传输速率；已知总大小时还显示剩余时间、
百分比与进度条。常用于 tar/ssh 管道传输大文件。

## 功能概述
- 数据流透传（stdin/stdout 或 -if/-of 文件）
- 显示已传输字节数与实时速率
- 已知大小时显示 ETA、百分比与进度条
- `--help` / `--version` / 缓冲区与限速等选项

## OHOS 适配要点
- 2001 年版 config.guess/config.sub 不识别 HarmonyOS 与 linux-ohos/aarch64，在 build() 内联修补（E007）
- 沙箱禁运行 conftest：cross.cache + 命令行 `ac_cv_prog_cc_works/cross=yes` 双保险
- HMDFS 临时目录需放开 umask 077，构建全程使用 -j1（E011/E074）
- 零外部依赖，产物仅 `bar` 可执行文件

## 依赖关系
- 无外部依赖

## 参考资料
- [clpbar 官方主页](http://clpbar.sourceforge.net)
- [SourceForge 文件页](https://sourceforge.net/projects/clpbar/files/clpbar/bar-1.11.1/)

## conan
```bash
conan create archives/c/clpbar/1.11.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
