# cyclone 11.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4
- CMake版本: 4.1.2
- 状态: built

## 编译步骤

1. **源码下载**：
   - 国内镜像加速器（ghfast.top、gh-proxy.com、ghp.ci）均无法访问（SSL证书验证失败）
   - 使用 Python urllib 直接从 GitHub 官方源下载：
   ```
   https://github.com/eclipse-cyclonedds/cyclonedds/archive/refs/tags/11.0.1.tar.gz
   ```

2. **CMake 配置**：
   ```bash
   cd ~/builds/cyclone-11.0.1.work/build
   cmake .. -DBUILD_DDSPERF=OFF
   ```

   注意：禁用了 ddsperf 构建，因为存在库加载路径问题。

3. **编译**：
   ```bash
   make
   ```

   编译成功，生成以下二进制文件：
   - bin/idlc (174KB)
   - lib/libddsc.so (1.89MB)
   - lib/libcycloneddsidl.so (264KB)
   - lib/libcycloneddsidlc.so (76KB)
   - lib/libddsrt-internal.a (217KB)
   - lib/libidlpp.a (325KB)

4. **安装到 staging 目录**：
   ```bash
   make install DESTDIR=/storage/Users/currentUser/test-install-cyclone-11.0.1
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 国内镜像加速器无法访问 | SSL证书验证失败/DNS解析失败 | 使用 GitHub 官方源直接下载 |
| 2 | ddsperf 构建时库加载失败 | CMake 相对路径 RPATH 在鸿蒙平台无法正确解析 | 禁用 ddsperf 构建（-DBUILD_DDSPERF=OFF） |
| 3 | CMake 识别平台警告 | OHOS 未在 CMake 平台列表中 | 警告不影响编译，可忽略 |

## 源码修改

无源码修改，不需要补丁。

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- 无其他依赖（OpenSSL可选，本编译未启用）

## 验证结果

```bash
# 验证 idlc 可执行
~/builds/cyclone-11.0.1.work/build/bin/idlc --version
# 输出：idlc version 11.0.1

# 验证库文件
ls -lh ~/builds/cyclone-11.0.1.work/build/lib/
# libddsc.so: 1.89MB
# libcycloneddsidl.so: 264KB
# libcycloneddsidlc.so: 76KB
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cyclone-11.0.1-ohos-aarch64.tar.gz | TBD | 预编译包（待创建） |
| manifest.yaml | 2KB | 归档元数据 |
| notes.md | 4KB | 编译笔记 |
| quality-report.md | 1KB | 质量报告 |
| test-report.md | 1KB | 测试报告 |

## 注意事项

1. **ddsperf 已禁用**：由于库加载路径问题，本编译禁用了 ddsperf 工具。如果需要 ddsperf，需要修复 CMake RPATH 配置。
2. **国内镜像问题**：所有国内 GitHub 加速器均无法访问，建议后续编译直接使用 GitHub 官方源。
3. **CMake 平台警告**：CMake 无法识别 OHOS 平台，输出警告但不影响编译。

## 编译结束

**编译结束**: 2026-05-27 11:07
**最终状态**: built
**编译耗时**: 约10分钟（下载+配置+编译+安装）
**下载源**: GitHub 官方源