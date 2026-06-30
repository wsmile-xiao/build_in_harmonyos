# libsndfile

## 简介

libsndfile 是一个 C 库，用于读写包含采样音频数据的文件。它支持多种音频格式，包括 WAV、AIFF、AU、FLAC、OGG/Vorbis 等，并提供完整的 API 用于音频文件的创建、读取和操作。

## OHOS 适配要点

### 构建系统选择
- libsndfile 支持 Autotools 和 CMake 两种构建系统
- 在 OHOS 平台上，由于 autotools 的 config.status 临时文件创建机制存在权限限制（TMPDIR 问题），推荐使用 **CMake** 构建

### 平台识别补丁
需要修改 `build-aux/config.guess` 和 `build-aux/config.sub` 以支持 HarmonyOS：

1. **config.guess**：
   - 在 `case $UNAME_SYSTEM in` 中添加 `HarmonyOS`
   - 添加 `__OHOS__` LIBC 检测分支
   - 添加 `aarch64:HarmonyOS:*:*` case 返回 `aarch64-unknown-linux-ohos`

2. **config.sub**：
   - 添加 `ohos-linux` 处理块（设置 `basic_os=linux-ohos`）
   - 在 OS 列表中添加 `ohos*`
   - 在 kernel-os 组合检查中添加 `linux-ohos*`

### CMake 配置参数
```bash
cmake .. \
    -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DENABLE_EXTERNAL_LIBS=ON \
    -DCMAKE_PREFIX_PATH=$HOME/usr/local
```

## 依赖关系

### 编译依赖
| 依赖 | 版本 | 说明 |
|------|------|------|
| libogg | 1.3.6 | OGG 容器格式支持 |
| libvorbis | 1.3.7 | Vorbis 音频编码支持 |
| flac | 1.4.3 | FLAC 无损音频支持 |
| opus | 1.4 | Opus 低延迟音频编码支持（可选） |

### 安装预编译依赖
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libogg 1.3.6
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- flac 1.4.3
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- opus 1.4
# libvorbis 需要单独编译（无预编译包）
```

## 提供的工具

编译后提供以下可执行工具：
- `sndfile-info` - 显示音频文件信息
- `sndfile-play` - 播放音频文件
- `sndfile-convert` - 转换音频格式
- `sndfile-cmp` - 比较两个音频文件
- `sndfile-metadata-set/get` - 设置/获取元数据
- `sndfile-interleave/deinterleave` - 交错/去交错处理
- `sndfile-concat` - 拼接音频文件
- `sndfile-salvage` - 损坏文件修复

## 已编译版本

| 版本 | 状态 | 日期 | 构建系统 |
|------|------|------|----------|
| 1.2.2 | built | 2026-05-20 | CMake |

## 相关链接

- 官方网站: http://libsndfile.github.io/libsndfile/
- GitHub: https://github.com/libsndfile/libsndfile