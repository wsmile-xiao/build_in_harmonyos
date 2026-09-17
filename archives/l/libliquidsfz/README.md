# liquidsfz

## 简介

liquidsfz 是一个 SFZ v1 采样器库（C++17），可以把 SFZ 乐器定义文件与采样
（WAV/FLAC 等，经 libsndfile 读取）渲染成音频，附带 JACK 命令行播放器与 LV2
插件两个可选前端。核心库无音频/图形服务依赖，纯 POSIX + C++17 + libsndfile。

## 功能概述

- 解析 SFZ v1 采样器定义（region/opcodes、循环、包络、氢鼓机导入等）
- 按需 mmap 采样加载 + 后台预加载线程（POSIX mmap / std::thread）
- 实时渲染 API（`LiquidSFZ::Synth`：note on/off、CC、pitch bend、process）
- 可选 JACK CLI 播放器（`--with-jack`，OHOS 不启用）
- 可选 LV2 插件（`--with-lv2`，依赖 X11 系，OHOS 不启用）

## OHOS 适配

- 上游默认只构建静态库（AC_DISABLE_SHARED + LT_INIT pic-only），OHOS 沿用
  该形态：`lib/libliquidsfz.a` + 头文件 `liquidsfz.hh` + `liquidsfz.pc`
- 归档捆绑 2018 旧式 config.guess/config.sub（无 GUESS= 变量），无法识别
  HarmonyOS 主机：按 E564 方法打 `0001-config-guess-sub-ohos.patch`
  （config.guess 增加 `aarch64:HarmonyOS` 分支；config.sub 双锚点接受
  `linux-ohos`）
- configure/make/check/install 全程 `SHELL/CONFIG_SHELL=/system/bin/sh`
  （规避 profile buildenv bash 导致的 libtool 引号转义与 HMDFS getcwd 问题），
  configure 内两处 `umask 077` 改写为 `umask 022`（E011），TMPDIR 指向构建
  目录内 `.tmp`，make 串行执行
- `--without-jack --without-lv2` 显式关闭可选前端（OHOS 无 jackd 运行时、
  无 X11/xrandr/xcursor 栈）
- libsndfile 经 pkg-config（PKG_CHECK_MODULES）发现，conan 侧由
  PkgConfigDeps 生成 sndfile.pc 并显式注入 PKG_CONFIG_PATH

## 依赖关系

| 依赖 | 角色 | 说明 |
|------|------|------|
| libsndfile | 硬依赖（必选） | 采样读取/测试 wav 生成，pkg-config `sndfile` |
| jack + readline | 可选（默认开） | OHOS 关闭 |
| lv2 + gl/x11/xext/xrandr/xcursor | 可选（默认开） | OHOS 关闭 |
| fftw3/fftw3f | 可选测试（默认关） | 不引入 |

## 参考资料

- 官方网站/仓库: https://github.com/swesterfeld/liquidsfz
- License: MPL-2.0（归档内 3rdparty pugixml/imgui/pugl 仅 LV2 GUI 路径使用，
  关闭 LV2 后不参与构建）
