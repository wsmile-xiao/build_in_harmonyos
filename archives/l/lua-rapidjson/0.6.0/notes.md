# lua-rapidjson 0.6.0 编译笔记

## 编译环境
- 平台: OpenHarmony NEXT (musl libc)
- 编译器: clang
- 构建系统: CMake

## 编译步骤
1. 下载源码: lua-rapidjson-0.6.0.tar.gz
2. 解压到构建目录
3. CMake 配置:
   - cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
           -DLUA_INCLUDE_DIR=$HOME/usr/local/include \
           -DLUA_LIBRARIES=$HOME/usr/local/lib/liblua.a \
           -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
           ..
4. make -j2 编译
5. make install DESTDIR=$TEST_PREFIX 安装到 staging 目录

## 问题与方案
- **问题**: CMake 版本兼容性
  - **方案**: 添加 CMAKE_POLICY_VERSION_MINIMUM=3.5 参数

- **问题**: Lua 静态库链接
  - **方案**: 使用 Lua 5.4.7 静态库（-fPIC 编译）

## 验证结果
- 编译成功，生成 rapidjson.so (466KB)
- 质量门禁 G0-G4 全部通过
- ELF 签名完成

## 交付物
- 预编译包: lua-rapidjson-0.6.0-ohos-aarch64.tar.gz (613KB)
- 调试符号包: lua-rapidjson-0.6.0-ohos-aarch64-debug.tar.gz (246KB)

---
**编译结束**: 2026-06-12
**最终状态**: success
