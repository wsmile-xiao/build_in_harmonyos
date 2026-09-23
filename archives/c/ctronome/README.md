# ctronome — 命令行节拍器

ctronome 是一个极简的可编程命令行节拍器（C 语言，2014 年发布）。它把两个
WAV 采样文件循环写入 OSS 音频设备来产生节拍，支持 BPM、拍号、节拍程序
文件与重复次数等参数。

## 功能概述

- 命令行节拍器，BPM 范围 30–250，拍号支持 3/4、7/8 等
- 声音素材外置：用 `-w1` / `-w2` 指定首拍与其余拍的 WAV 文件
- `-p programfile` 用程序文件描述多段不同的节奏
- `-c count` 指定播放次数后退出
- `-d device` 指定 OSS 输出设备（默认 /dev/dsp）
- `-h` 打印用法，`-v` 打印版本横幅

## OHOS 适配要点

- **无 configure 脚本**：项目是顶层裸 Makefile 工程，且只有 `all` 与
  `clean` 两个目标，没有 install / check，打包在 `conanfile.py` 的
  `package()` 中完成
- **补丁 0001/0002（portability，无平台宏）**：`ctronome.h` 里把
  `programfile`、`dsp_channels`、`dsp_format`、`dsp_speed`、`dsp_depth`、
  `debug` 以“暂定义”形式重复定义（依赖 GCC 10 以前的 common symbol 合并
  语义），clang 15 默认 `-fno-common` 会在链接期报 12 处 `duplicate symbol`；
  补丁把这 6 个暂定义改成 `extern` 声明并在 `ctronome.c` 中给出唯一一份
  定义。**刻意不用 `-fcommon`**（知识库 E491 明确禁止——它会掩盖非法的
  声明/定义关系）
- **编译标志只能随 CC 传**：Makefile 的编译规则写作 `$(CC) -c $<`，
  不引用 `$(CFLAGS)`
- **OSS 头文件无需移植**：`sys/soundcard.h` 与 `linux/soundcard.h` 由
  OHOS SDK sysroot 直接提供
- **平台限制**：音频输出依赖 OSS `/dev/dsp`，HarmonyOS PC 没有该字符
  设备，程序会打印 `FATAL: cannot open dsp device /dev/dsp` 后退出；
  参数解析、WAV 头解析、节拍模式计算等其余功能正常

## 源码

- 官方发布页：https://sourceforge.net/projects/ctronome/
- 本次使用：ctronome-0.5.6.tar.gz
  （sha256 d8c17282235759491eae36efbc8fe93514dcac655efa68d3cb8db0132c29a24d）

## 版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 0.5.6 | built | 2026-09-14 | 首次适配 HarmonyOS PC（aarch64）；2 个 portability 补丁，无平台宏 |
