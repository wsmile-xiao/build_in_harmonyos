# aom 3.9.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 源码准备: 使用已有源码目录 `/storage/Users/currentUser/tmpexport/builds/libaom-3.9.1.orig`
2. 创建 tarball: `tar czf aom-3.9.1.tar.gz libaom-3.9.1.orig`
3. 静态库编译:
   ```bash
   mkdir build-ohos && cd build-ohos
   cmake .. -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
            -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
            -DCMAKE_SYSTEM_NAME=Linux \
            -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
            -DCMAKE_INSTALL_PREFIX=/usr/local \
            -DAOM_TARGET_CPU=generic \
            -DCMAKE_BUILD_TYPE=Release \
            -DENABLE_TESTS=OFF \
            -DENABLE_EXAMPLES=OFF \
            -DENABLE_DOCS=OFF
   make -j4
   make install DESTDIR=/storage/Users/currentUser/tmpexport/test-install-aom-3.9.1
   ```
4. 动态库编译:
   ```bash
   mkdir build-ohos-shared && cd build-ohos-shared
   cmake .. ... -DBUILD_SHARED_LIBS=ON
   make -j4
   make install DESTDIR=/storage/Users/currentUser/tmpexport/test-install-aom-3.9.1-shared
   ```
5. 打包:
   ```bash
   tar czf aom-3.9.1-ohos-aarch64.tar.gz usr/local/ (静态库)
   tar czf aom-3.9.1-ohos-aarch64-shared.tar.gz usr/local/ (动态库)
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 无法识别 HarmonyOS 平台 | CMake 没有 HarmonyOS Platform 模块 | 使用 CMAKE_SYSTEM_NAME=Linux 作为 workaround |
| 2 | 源码 build/cmake 目录缺失 | 打包时目录结构不完整 | 从 .orig 目录复制完整的 build/cmake 到 .work |
| 3 | 汇编优化不支持 | HarmonyOS 平台未支持 | 使用 AOM_TARGET_CPU=generic 禁用汇编 |

## 源码修改

无源码修改，仅添加编译配置文档 patch: 0001-harmonyos-build-config.patch

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- perl: 5.42.0
- git: 2.45.2

## 验证结果

```bash
# 静态库
ls -lh archives/a/aom/3.9.1/packaging/aom-3.9.1-ohos-aarch64.tar.gz
-rw-rw---- 1 20001006 file_manager 6.1M  aom-3.9.1-ohos-aarch64.tar.gz

# 动态库
ls -lh archives/a/aom/3.9.1/packaging/aom-3.9.1-ohos-aarch64-shared.tar.gz
-rw-rw---- 1 20001006 file_manager 11M  aom-3.9.1-ohos-aarch64-shared.tar.gz

# 库文件
libaom.a: 静态库 (6.0MB)
libaom.so.3.9.1: 动态库 (包含 so 链接)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| aom-3.9.1-ohos-aarch64.tar.gz | 6.1M | Release 静态库版本 |
| aom-3.9.1-ohos-aarch64-debug.tar.gz | 26M | Debug 静态库版本（含调试符号） |
| aom-3.9.1-ohos-aarch64-shared.tar.gz | 11M | Release 动态库版本（可选） |
| 0001-harmonyos-build-config.patch | 1KB | 编译配置文档 |

## 注意事项

1. 必须使用 AOM_TARGET_CPU=generic 禁用汇编优化，否则编译失败
2. 必须指定 CMAKE_SYSTEM_NAME=Linux，CMake 不支持 HarmonyOS 平台
3. 构建目录必须与源码目录分离（CMake 要求）
4. 动态库版本需要额外添加 -DBUILD_SHARED_LIBS=ON 参数
