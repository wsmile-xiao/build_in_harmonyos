# Draft: autotools cross mode "assumed OK" optional-dep probes enable absent targets

**ID**: libtheora-1.2.0-alpha1-cross-mode-assumed-optional-deps
**Severity**: 2 | **Category**: build-system|configure|ohos
**Status**: DRAFT

## 症状

用 `--host=aarch64-linux-ohos --build=aarch64-unknown-linux-gnu`（sdl-image/aalib
惯例）强制交叉模式后，构建在 examples/ 失败：

```
checking for Vorbis... cross compiling; assumed OK...
examples/encoder_example.c:48:10: fatal error: 'vorbis/codec.h' file not found
```

## 根因

上游宏（XIPH_PATH_VORBIS）在交叉模式下无法运行探测程序，就"假定依赖可用"，
启用依赖 vorbis 的 noinst 示例程序；而 libvorbis 并不是本包的依赖，头文件不存在。

## 修复

若交叉模式的唯一动机是老 config.guess，则改用**原生模式 + vendored 现代补丁对**
（babeltrace2 2.1.2 的 patches/autotools/config/，GNU 2023-08-22 基座；2010 年
libtheora tarball 自带 2003 版，patch-autotools-ohos.pl 都匹配不上）。原生模式下
vorbis pkg-config 探测干净失败，可选示例自动跳过（上游原生行为），核心库完整构建、
零裁剪。配合 E011 umask/mktemp 补丁与共享依赖 LD_LIBRARY_PATH 注入（见姊妹草稿）。

**经验法则**：dual-triplet 交叉模式适用于"conftest 完全跑不了"；当上游宏在交叉
模式下对可选依赖做环境无法满足的"假定"时，必须原生模式。

## 验证

libtheora 1.2.0-alpha1：交叉模式死在 examples（vorbis/codec.h）；原生模式 +
vendored 2023 config 对 + E011 补丁 configure 干净通过，三库全建，9/9 上游测试
+ 消费者往返 test_package 全绿。

*2026-09-18 — libtheora 1.2.0-alpha1 适配过程中实测*
