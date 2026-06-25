# pcaudiolib 1.3 编译记录

## 基本信息
- 软件：pcaudiolib (Portable C Audio Library)
- 版本：1.3
- 构建系统：autotools
- 源码来源：GitHub clone (因网络问题无法下载官方 tarball)

## 编译日期
2026-05-19

## 编译环境
- 平台：aarch64-unknown-linux-ohos (HarmonyOS)
- 编译器：clang 15.0.4 (gcc wrapper)
- 构建工具：手动 Makefile (autotools config.status 因 HMDFS 临时文件问题失败)

## 编译过程

### 遇到的问题

1. **源码下载问题**
   - GitHub 官方 tarball 无法下载（SSL 证书和网络问题）
   - 解决：从 GitHub clone 源码仓库

2. **autotools 初始化问题**
   - 从 git clone 的源码缺少 configure 脚本
   - 解决：手动运行 autogen.sh 生成 configure
   - 需要创建 bash/sed 的软链接修复 libtoolize

3. **平台识别问题**
   - config.guess 无法识别 HarmonyOS 平台
   - 解决：使用 patch-autotools-ohos.pl 补丁，并手动修改 config.sub 支持 linux-ohos

4. **HMDFS 临时文件问题**
   - config.status 在 HMDFS 文件系统上无法创建临时子目录
   - 解决：手动创建 Makefile 和 config.h，手动编译

### 编译配置
- 支持的音频后端：OSS (sys/soundcard.h)
- 不支持：PulseAudio、ALSA（缺少依赖库）

### 手动编译命令
```bash
gcc -Wall -fPIC -I./src/include -I./src -c src/audio.c -o audio.o
gcc -Wall -fPIC -I./src/include -I./src -c src/oss.c -o oss.o
gcc -Wall -fPIC -I./src/include -I./src -c src/alsa.c -o alsa.o
gcc -Wall -fPIC -I./src/include -I./src -c src/pulseaudio.c -o pulseaudio.o
gcc -Wall -fPIC -I./src/include -I./src -c src/qsa.c -o qsa.o
gcc -shared -o libpcaudio.so audio.o oss.o alsa.o pulseaudio.o qsa.o
ar rcs libpcaudio.a audio.o oss.o alsa.o pulseaudio.o qsa.o
```

## 编译产物
- libpcaudio.so (22848 bytes)
- libpcaudio.a (10240 bytes)
- audio.h (头文件)

## 测试
- 无测试套件（make check 不适用）

## 安装位置
- 库文件：$DEFAULT_PREFIX/lib/
- 头文件：$DEFAULT_PREFIX/include/pcaudiolib/
---

**编译结束**: 2026-05-19 13:07
**最终状态**: built
---

**编译结束**: 2026-05-19 14:49
**最终状态**: built
