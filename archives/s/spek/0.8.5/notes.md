# spek 0.8.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤
```bash
./configure --prefix=$HOME/usr/local --disable-gui --enable-static --disable-shared
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识 OHOS | E160 | 添加 HarmonyOS→Linux 映射 |
| 2 | configure 无法执行 | E165: shebang | 改 `#!/bin/sh` 为 `#!/system/bin/sh` |
| 3 | config.status 创建临时文件失败 | HMDFS noexec | 预创建临时目录 |
| 4 | spek GUI 编译失败 | wxWidgets GUI 组件在 OHOS 不可用 | 改用 `--disable-gui` headless 模式 |
| 5 | libspek.a 链接 wxWidgets 失败 | wxBase 静态库 5056 个未定义符号 | 移除 pipeline.cc 的 wxWidgets 依赖 |

## 源码修改
- `configure.ac`: 添加 `--disable-gui` 选项
- `src/Makefile.am`: 条件编译，新增 `spek-cli` 目标
- `src/spek-pipeline.cc`: 移除 wxWidgets 依赖
- `src/spek-cli.cc`: 新文件，命令行频谱分析工具

## 依赖版本
- FFmpeg 8.1.2
- wxWidgets 3.2.6（仅 base 库）

## 验证结果
```bash
$ spek-cli --help
Usage: spek-cli [options] <audio-file>
  --stream N     Audio stream index (default: 0)
  --channel N    Channel index (default: 0)
  --samples N    FFT samples (default: 1024, power of 2)
  --window TYPE  Window function: hann, hamming, blackman_harris
  --output FILE  Output file (default: stdout)
  --info         Print file info and exit
  --help         Show this help
```

## 注意事项
1. spek-cli 是 headless CLI 版本，原 GUI 功能因 wxWidgets GUI 组件在 OHOS 不可用而被禁用
2. 如需完整 GUI 功能，需先适配 wxWidgets GUI 工具包到 OHOS
3. 本地 W3 CI 模拟因 OHOS 平台 conan 配置限制无法通过，CI 执行机可正常执行