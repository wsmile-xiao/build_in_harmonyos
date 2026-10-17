# jnoise -- JACK 白噪/粉噪发生器

## 软件简介

jnoise 是 Fons Adriaensen（`clthreads`/`zita-alsa-pcmi`/`aeolus` 作者）写的**命令行 JACK 客户端**，
在两个输出端口上同时产生**白噪声**与**粉噪声**，两者都是高斯幅度分布，输出电平为
-20 dB RMS（相对满幅正弦）。常用于给音频链路做噪声激励、频响测量与校准。

**主要功能**:
- 单命令启动，可选一个电平参数（dB，上限 -10 dB）
- 两个输出端口：`white`（白噪）与 `pink`（粉噪，IIR 着色滤波）
- 随机源为 55 抽头 PRBS（`rngen.cc`/`prbsgen.h`），经 Box-Muller 变换得到高斯分布

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 0.6.0 | built | 2026-09-25 | 1 |

## 使用方法

```bash
# 默认 -20 dB RMS；参数是输出电平（dB），最高只允许 -10 dB
jnoise
jnoise -20

# 电平过高时直接拒绝并退出 1
jnoise 0
# Level is too high, max = -10dB
```

需要一个正在运行的 JACK server（上游以 `JackNoStartServer` 连接，不会自己拉起 server）。

## 平台适配说明

### 鸿蒙系统适配

**编译补丁**（`0.6.0/patches/0001-source-Makefile.patch`，portability）:
1. 链接命令里硬编码的 `g++` 改为 `$(CXX)`（OHOS 无 g++，编译器须由 conan profile 提供，R33）
2. install 目标的裸 `install` 参数化为 `INSTALL ?= /bin/install`（OHOS 无 coreutils install，toybox 在 /bin/install）

`PREFIX = /usr/local` 是普通赋值，由配方在 make 命令行覆盖为 `PREFIX=/` + `DESTDIR=<package_folder>`，
不需补丁；上游的 `-DSHARED="$(PREFIX)/share"` 宏在 0.6.0 源码中从未被引用，故无运行期烧路径问题。

**编译依赖**: jack/1.9.22（`-ljack`）

**构建系统**: makefile（无 configure 脚本；Makefile 位于 tarball 的 `source/` 子目录）

### 已知平台限制

- **运行期需要 JACK server**：本包只产出客户端二进制。本机与 CI worker 上都没有运行中的
  `jackd`，因此 `jack_client_open()` 返回 NULL、程序打印 `Can't connect to JACK` 并退出 1；
  噪声输出分支（`jack_activate` 之后的回调）因此**未执行**（未执行不等于失败，探针证据见
  `0.6.0/notes.md`）。
- 上游无图形界面、无测试套件（Makefile 只有 all/install/clean）。

## 验证结果

| 测试项 | 结果 |
|--------|------|
| `conan create`（含 test_package） | 通过 |
| W3 本地 CI（finish step5） | 通过 |
| test_package 消费者断言 | 6/6 通过 |
| 上游测试用例 | 0（上游无 check/test 目标，四形态逐形自数见 notes.md） |

## 源码信息

- **源码地址**: https://kokkinizita.linuxaudio.org/linuxaudio/downloads/jnoise-0.6.0.tar.bz2
- **官方主页**: https://kokkinizita.linuxaudio.org/linuxaudio/
- **许可证**: GPL-2.0-or-later
- **作者**: Fons Adriaensen <fons@kokkinizita.net>

## 相关资源

- [编译详情](./0.6.0/notes.md)
