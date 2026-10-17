# libgeocoding

Google **libphonenumber** 的**离线电话号码地理编码**库（C++）。

- 上游仓库：<https://github.com/google/libphonenumber>
- 构建入口：上游源码树子目录 `cpp/`（CMake）
- 公开头：`phonenumbers/geocoding/phonenumber_offline_geocoder.h`（以及同源 `phonenumbers/phonenumberutil.h`）
- 归档产物：`libgeocoding.a` + `libphonenumber.a`（离线 geocoder 复用号码解析与元数据，二者必须同时链接）

## 与 libphonenumber 的关系

`libgeocoding` 与 `libphonenumber` **同源同配方**：上游 `cpp/CMakeLists.txt` 一次配置同时产出

```
cpp/CMakeLists.txt:459  add_library (phonenumber STATIC ${SOURCES})
cpp/CMakeLists.txt:464  add_library (geocoding   STATIC ${GEOCODING_SOURCES})   # BUILD_GEOCODER=ON
```

Debian 亦为同一源包拆分出的两个二进制（`libphonenumber8` + `libgeocoding8`）。
因此本包不依赖 `libphonenumber` 包，而是直接从同一上游源码树构建并一并导出两个归档。

## 依赖

| 依赖 | 版本 | 类型 |
|---|---|---|
| abseil-cpp | 20260107.1 | 直接链接（`absl::node_hash_set/strings/synchronization`） |
| protobuf | 33.6 | 直接链接 + 构建期 `protoc` |
| icu4c | 78 | 直接链接（`icuuc` + `icui18n`，geocoder 强制 i18n） |
| googletest | 1.12.1 | 构建期测试（`test_requires`，不向下游传播） |

## 适配要点

1. **abseil 弃用 API**：abseil 20260107.1 已弃用 `absl::MutexLock(&mutex)`，而上游 `-Wall -Werror` 使其成为硬错误 → 目标库源码 `phonenumber_offline_geocoder.cc` 改用非弃用构造。
2. **静态依赖闭包**：上游只 `find_library` 出 `icuuc/icui18n/protobuf`，静态归档不携带自身依赖 → 由配方按真实依赖图补齐 `icudata`、protobuf 引用的其余 Abseil 库、`utf8_range/utf8_validity`、`zlib`。
3. **abseil 发现路径**：Conan 只把依赖目录放进 `CMAKE_LIBRARY_PATH/INCLUDE_PATH`，`find_package(absl)` 会落空并转入 `FetchContent` 拉 GitHub（CI 无外网）→ 配方显式设置 `absl_DIR`。
4. **CMake 生成器必须 Ninja**：Makefile 生成器会给上游「空 `echo` 自定义命令」加 `.DELETE_ON_ERROR`，一执行就删掉随包发布的 `test_metadata.cc` → 编译失败。
5. 无关依赖剪枝：`REGENERATE_METADATA=OFF`（无 Java/Maven）、`USE_BOOST=OFF` + `USE_STDMUTEX=ON`（无 Boost 链）、`USE_RE2=OFF`（正则由 ICU 承担）。
