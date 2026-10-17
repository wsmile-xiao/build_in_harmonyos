# libfdk

## 简介
Fraunhofer FDK AAC 编解码库，提供高质量 AAC 编码与解码能力，独立无外部依赖。

## OHOS 适配
- CMake 构建，`BUILD_PROGRAMS=OFF` 仅安装库与头文件，保持纯库形态
- 无 conan 依赖，原生 OHOS aarch64 构建
- 上游 `test/run-test.sh` 需要联网下载 WAV 与 ffmpeg，真机以内存合成 PCM 离线镜像 stereo/mono 两路验证

## 依赖
- 无外部依赖

## 参考
- 上游仓库: https://github.com/mstorsjo/fdk-aac
- 发布包: https://downloads.sourceforge.net/project/opencore-amr/fdk-aac/fdk-aac-2.0.3.tar.gz
- ConanCenter 参考: recipes/libfdk_aac
