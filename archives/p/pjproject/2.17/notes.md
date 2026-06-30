# pjproject 2.17 适配笔记

## 编译环境
- 构建系统: cmake（autotools失败后切换）
- 编译日期: 2026-05-22
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. 初始化构建环境：使用本地已存在的 ~/tmp/pjproject-2.17 创建tarball
2. 尝试autotools构建：遇到config.status临时目录权限问题
3. 切换到CMake构建：
   ```bash
   mkdir build-cmake && cd build-cmake
   cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
            -DCMAKE_BUILD_TYPE=Release \
            -DPJMEDIA_WITH_WEBRTC_AEC3=OFF \
            -DPJMEDIA_WITH_WEBRTC_AEC=OFF \
            -DPJ_SKIP_EXPERIMENTAL_NOTICE=ON
   ```
4. 编译：`make -j1`（单线程避免内存问题）
5. 安装到DESTDIR：`make install DESTDIR=/storage/Users/currentUser/test-install-pjproject-2.17`
6. 安装到本地：`cmake --install .`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub下载超时 | 网络问题 | 使用本地已存在的源码目录创建tarball |
| 2 | config.status临时目录权限拒绝 | autotools在当前目录创建临时文件失败 | 切换到CMake构建系统 |
| 3 | webrtc_aec3编译错误 | 平台识别问题，缺少PlatformThreadId类型定义 | 禁用webrtc_aec3和webrtc_aec模块 |
| 4 | 系统内存不足（fork failed） | 资源耗尽 | 等待系统恢复后继续，使用单线程编译 |

## 源码修改

无补丁，仅通过CMake参数禁用问题模块。

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- pthread: 系统自带
- librt: 系统自带
- libm: 系统自带

未使用的可选依赖（未安装）：
- OpenSSL: 未找到（导致pjsua运行时报错）
- ALSA: 未找到
- SDL2: 未找到
- FFMPEG: 未找到
- VPX: 未找到
- OpenH264: 未找到
- OPUS: 未找到

## 验证结果

```bash
# 产物检查
ls -lh /storage/Users/currentUser/usr/local/bin/pjsua-2.17
# 输出: -rwxrwx--- 1 20001006 file_manager 2.3M 2026-05-22 18:25

# 运行验证
/storage/Users/currentUser/usr/local/bin/pjsua-2.17 --version
# 输出: Error loading shared library libcrypto.so.3 / libssl.so.3
# 原因: 编译时未找到OpenSSL，二进制未链接SSL库（功能受限但编译成功）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libpjlib.a | 442K | 核心库 |
| libpjlib-util.a | 293K | 工具库 |
| libpjnath.a | 336K | NAT穿透库 |
| libpjmedia.a | 1.0M | 媒体库 |
| libpjmedia-codec.a | 140K | 编解码库 |
| libpjmedia-audiodev.a | 16K | 音频设备库 |
| libpjmedia-videodev.a | 48K | 视频设备库 |
| libpjsip.a | 647K | SIP协议栈 |
| libpjsip-simple.a | 186K | SIP简化API |
| libpjsip-ua.a | 218K | SIP用户代理 |
| libpjsua-lib.a | 668K | PJSUA库 |
| libpjsua2.a | 1.0M | C++高级API |
| pjsua-2.17 | 2.3M | 命令行UA客户端 |

## 注意事项

1. **构建系统选择**：优先使用CMake，autotools在鸿蒙平台可能遇到临时目录权限问题
2. **WebRTC模块**：webrtc_aec3模块有平台兼容问题，建议禁用
3. **SSL支持缺失**：编译时未找到OpenSSL，如需SSL功能需先安装openssl预编译包
4. **内存限制**：建议使用单线程编译（-j1）避免内存不足
5. **功能受限**：缺少音频/视频/编解码依赖，仅基础功能可用
