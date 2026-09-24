# snapcast 0.35.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-25
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built (conan recipe generated)

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build snapcast 0.35.0 --url=https://github.com/snapcast/snapcast/archive/refs/tags/v0.35.0.tar.gz`
2. 应用 4 个 OHOS 适配补丁
3. Conan 安装依赖 (alsa-lib, boost, flac, libvorbis, opus, libsoxr, openssl, expat)
   - libogg/1.3.6 override=True 解决 flac(1.3.5)/libvorbis(1.3.6) 版本冲突
4. cmake 配置 (BUILD_WITH_AVAHI=OFF, BUILD_WITH_TREMOR=OFF, etc.)
5. cmake --build . -j2
6. cmake --install . --prefix $TEST_PREFIX
7. 生成 conanfile.py + conandata.yml + test_package/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_setcancelstate undeclared | OpenHarmony musl libc 缺少 pthread 取消函数 | 创建 ohos_compat.h(声明)+ohos_compat.cpp(stub), CMake -include 强制注入 |
| 2 | Avahi 不可用 | 无 avahi-client 预编译包 | BUILD_WITH_AVAHI=OFF |
| 3 | CMAKE_SYSTEM_NAME 为 "HarmonyOS" | 平台检测 | 使用 MATCHES "HarmonyOS" 条件判断 |
| 4 | OpenSSL::Crypto target not found | Conan 生成 openssl::openssl, snapcast 用 OpenSSL::SSL/Crypto | CMakeLists.txt 添加 alias targets |
| 5 | -lasound not found | pkg_search_module ALSA_LIBRARIES 不含 -L 路径 | conanfile.py generate() 设置 LIBRARY_PATH |
| 6 | libogg 版本冲突 | flac pins 1.3.5, libvorbis pins 1.3.6 | self.requires("libogg/1.3.6", override=True) |

## 源码修改

- CMakeLists.txt: 添加 __OHOS__ 定义、-include ohos_compat.h、OpenSSL target aliases
- common/CMakeLists.txt: 添加 ohos_compat.cpp 到 HarmonyOS 构建
- common/ohos_compat.cpp: pthread_setcancelstate stub 实现
- common/ohos_compat.h: pthread_setcancelstate stub 声明

补丁: 0001-CMakeLists.txt.patch, 0002-common-CMakeLists.txt.patch, 

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| alsa-lib | 1.2.16.1 | Conan registry |
| Boost | 1.84.0 | Conan registry |
| FLAC | 1.4.3 | Conan registry |
| libogg | 1.3.6 | Conan registry (override) |
| libvorbis | 1.3.7 | Conan registry |
| opus | 1.5.2.1 | Conan registry |
| libsoxr | 0.1.3 | Conan registry |
| OpenSSL | 1.1.1w | Conan registry |
| expat | 2.8.2.1.1 | Conan registry |

## 验证结果

```bash
$ snapserver --version
snapserver v0.35.0

$ snapclient --version
snapclient v0.35.0
```

## 注意事项

- Avahi 已禁用，mDNS 发现功能不可用 (avahi-client 未在 registry 发布)
- Tremor 已禁用 (upstream 默认 OFF)，使用 libvorbis 替代
- PulseAudio/JACK/PipeWire/SDL2 已禁用 (OHOS 不可用)
- libogg 使用 override=True 强制 1.3.6 解决版本冲突
---

**编译结束**: 2026-08-26 01:08
**最终状态**: built
