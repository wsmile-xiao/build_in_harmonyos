# mongoc-driver 1.29.0 — OpenHarmony Conan Recipe

## 基本信息
- 软件: mongoc-driver (libmongoc + libbson)
- 版本: 1.29.0
- 构建系统: CMake
- 目标: ohos-aarch64
- 状态: published (Conan recipe verified)

## 依赖关系
| 依赖 | 版本 | 来源 |
|------|------|------|
| OpenSSL | 1.1.1w | Conan 制品仓 |
| zlib | 1.3.1 | Conan 制品仓 |
| zstd | 1.5.7 | Conan 制品仓 |
| snappy | 1.2.2 | Conan 制品仓 |
| utf8proc | 2.8.0 | 源码内嵌 |

## 编译指导
```bash
conan create archives/m/mongoc-driver/1.29.0/conanfile.py \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## CMake 选项
- ENABLE_STATIC=ON / ENABLE_SHARED=OFF (静态库，避免 RPATH 问题)
- ENABLE_TESTS=OFF / ENABLE_EXAMPLES=OFF
- ENABLE_SNAPPY=ON / ENABLE_ZSTD=ON / ENABLE_ZLIB=SYSTEM
- ENABLE_SSL=OPENSSL
- USE_BUNDLED_UTF8PROC=ON (使用内嵌 utf8proc)
- ENABLE_CLIENT_SIDE_ENCRYPTION=OFF

## 关键适配
- OPENSSL_ROOT_DIR: 设置 OpenSSL 包目录
- ZLIB_ROOT: 设置 zlib 包目录
- CMAKE_PREFIX_PATH: 设置 snappy 搜索路径 (自定义 FindSnappy.cmake)
- PKG_CONFIG_PATH: 设置 zstd 的 pkg-config 路径

## 安装产物
- libbson-static-1.0.a (BSON 序列化库)
- libmongoc-static-1.0.a (MongoDB C 驱动)

## 功能验证
test_package/test_mongoc.cpp: 初始化 mongoc 驱动，创建 BSON 文档并转换为 JSON。
