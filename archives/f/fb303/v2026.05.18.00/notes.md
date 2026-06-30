# fb303 v2026.05.18.00 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 1. 配置 CMake（禁用 Thrift 服务）

```bash
cd /storage/Users/currentUser/builds/fb303-v2026.05.18.00.work
mkdir -p cmake-build && cd cmake-build

cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DENABLE_THRIFT_SERVICE=OFF \
  -Dglog_DIR=/storage/Users/currentUser/usr/local/lib/cmake/glog \
  -DGFLAGS_LIBRARY=/storage/Users/currentUser/usr/local/lib/libgflags.so
```

### 2. 编译

```bash
make -j2
```

### 3. 安装（staging）

```bash
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-fb303-v2026.05.18.00
```

### 4. 安装到本地

```bash
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | FBThrift 依赖失败 | FBThrift 需要 std::pmr 支持，OpenHarmony 暂不支持 | 禁用 Thrift 服务功能 |
| 2 | find_package(Glog) 失败 | Glog 目标名大小写问题 | 改为 find_package(glog CONFIG) |
| 3 | Thrift 依赖文件编译失败 | BaseService.cpp 等依赖 Thrift | 在 CMakeLists.txt 中排除这些文件 |

## 源码修改

### CMakeLists.txt 主要修改

1. **添加 ENABLE_THRIFT_SERVICE 选项**（默认 OFF）
   ```cmake
   option(ENABLE_THRIFT_SERVICE
     "Build Thrift RPC service support (requires FBThrift with std::pmr support)"
     OFF
   )
   ```

2. **修改 glog 查找方式**
   ```cmake
   find_package(glog CONFIG REQUIRED)  # 改为小写 glog
   ```

3. **条件编译 Thrift 相关代码**
   - 当 ENABLE_THRIFT_SERVICE=OFF 时，排除 BaseService.cpp 和 TFunctionStatHandler.cpp
   - 不链接 FBThrift 相关库

完整补丁见: patches/0001-disable-thrift-service.patch

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| folly | v2026.05.18.00 | Facebook 核心库 |
| glog | 0.7.1 | Google 日志库 |
| gflags | 2.2.2 | Google 命令行标志库 |

## 验证结果

```bash
# 检查静态库
ls -lh /storage/Users/currentUser/builds/fb303-v2026.05.18.00.work/cmake-build/libfb303.a
# -rw-r--r-- 1 20001006 file_manager 22M May 26 20:01 libfb303.a

# 检查安装文件
ls /storage/Users/currentUser/usr/local/include/fb303/ | head -5
# BaseService.h
# CallbackValuesMap-inl.h
# CallbackValuesMap.h
# DynamicCounters.h
# ExportType.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libfb303.a | 22MB | 静态库（核心功能，不含 Thrift 服务） |

## 注意事项

1. **Thrift 服务不可用**：由于 FBThrift 需要 std::pmr 支持，当前版本禁用了 Thrift 服务功能
2. **功能受限**：BaseService.cpp 和 TFunctionStatHandler.cpp 被排除，相关功能不可用
3. **后续改进**：如果 OpenHarmony 未来支持 std::pmr，可以重新启用 Thrift 服务
---

**编译结束**: 2026-05-26 20:19
**最终状态**: published
