# stk 5.0.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++ (clang 15.0.4)
- 平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

1. 从 GitHub 下载 stk 5.0.1 源码（Savannah 下载因 SSL 问题失败）
2. 手动设置 .orig 和 .work 目录
3. 运行 `autoreconf -fi` 生成 configure 脚本
4. 配置: `./configure --prefix=$DEFAULT_PREFIX --disable-realtime --enable-shared RAWWAVE_PATH=$DEFAULT_PREFIX/share/stk/rawwaves`
5. 编译: `make -C src -j1` (仅编译核心库，demo/effects 等因禁用 realtime 无法编译)
6. 安装: `make -C src install DESTDIR=$TEST_PREFIX` + 手动安装 libstk.a 和 rawwave 数据
7. 打包: `ohc-run.py package stk 5.0.1`
8. 本地安装: `make -C src install` + 手动安装 libstk.a 和 rawwave 数据

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah SSL下载失败 | SSL证书验证问题 | 用 wget 从 GitHub 下载，手动设置目录 |
| 2 | 无 configure 脚本 | GitHub 源码包不含预生成 configure | 运行 `autoreconf -fi` 生成 |
| 3 | 默认启用 ALSA 音频 API | 鸿蒙无 ALSA/PulseAudio | `--disable-realtime` 禁用所有音频 API |
| 4 | demo 编译失败 | demo 使用 RtAudio dac 对象 | 只编译核心库 (make -C src) |
| 5 | install 不安装静态库 | src/Makefile.in install 只安装共享库 | 手动 `install -m 644 libstk.a` |
| 6 | RAWWAVE_PATH 相对路径 | 默认 "../../rawwaves/" 是构建时相对路径 | `RAWWAVE_PATH=$PREFIX/share/stk/rawwaves` |
| 7 | rawwave 数据未安装 | install 目标不含数据文件安装 | 手动安装 .raw 文件到 share/stk/rawwaves/ |

## 源码修改

- config/config.guess: 更新以识别 aarch64-unknown-linux-ohos 平台
- config/config.sub: 更新以识别 aarch64-unknown-linux-ohos 平台

## 依赖版本

- libm (system math library)
- 无其他外部依赖 (--disable-realtime 禁用 ALSA/PulseAudio/JACK)

## 验证结果

stk 是纯库软件，无 --version 命令行工具。
- llvm-objdump 确认 libstk.a: valid ELF64 aarch64, 78 objects
- llvm-nm 确认 libstk.so: valid shared library with symbols
- 104 头文件已安装到 $PREFIX/include/stk/
- 41 rawwave 数据文件已安装到 $PREFIX/share/stk/rawwaves/

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| stk-5.0.1-ohos-aarch64.tar.gz | 4030KB (4127368 bytes) | 预编译包（含 ELF 签名） |
| stk-5.0.1-ohos-aarch64-debug.tar.gz | 286KB | debug symbols 包 |
| libstk.a | 1.7MB | 静态库 |
| libstk-5.0.0.so | 633KB | 共享库 |
| libstk.so | symlink → libstk-5.0.0.so | 共享库 symlink |

## 注意事项

- stk 在鸿蒙平台必须 --disable-realtime
- 静态库需手动安装（默认 install 不含）
- RAWWAVE_PATH 必须指向安装后的绝对路径
- demo/effects/ragamatic 项目在禁用 realtime 后无法编译
- 无 make check 目标，纯库软件无测试套
---

**编译结束**: 2026-06-03 15:09
**最终状态**: published
