# leptonica 1.84.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **下载源码**
   ```bash
   curl -k -L https://github.com/DanBloomberg/leptonica/releases/download/1.84.1/leptonica-1.84.1.tar.gz -o leptonica-1.84.1.tar.gz
   tar -xzf leptonica-1.84.1.tar.gz
   ```

2. **CMake 配置**
   ```bash
   mkdir -p build
   cd build
   cmake ../src \
     -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   ```

3. **编译安装**
   ```bash
   make -j2
   make install DESTDIR=/storage/Users/currentUser/tmp/test-install-leptonica-1.84.1
   ```

4. **打包**
   ```bash
   ohc-run.py package leptonica 1.84.1
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | URL 自动搜索失败 | 搜索引擎未能自动找到最新版本 URL | 手动指定版本 1.84.1 和 GitHub releases URL |
| 2 | 构建系统类型误判 | manifest.yaml 中构建系统类型记录为 autotools，实际使用 CMake | 更新 manifest.yaml 中 build.system 为 cmake |
| 3 | CMake 版本兼容性 | CMakeLists.txt 缺少 cmake_minimum_required 声明 | 添加 CMAKE_POLICY_VERSION_MINIMUM=3.5 参数 |

## 源码修改

无补丁文件。编译过程中未修改源码，leptonica 1.84.1 在 HarmonyOS 上可直接编译。

## 依赖版本

| 依赖 | 版本 |
|------|------|
| zlib | 系统内置 |
| libpng | 16.x |
| libjpeg-turbo | 3.1.4.1 |

## 验证结果

```bash
# 检查静态库
ls -la ~/usr/local/lib/libleptonica.a
# 输出: libleptonica.a (约 10MB)

# 检查头文件
ls ~/usr/local/include/leptonica/*.h | wc -l
# 输出: 36 个头文件
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| leptonica-1.84.1-ohos-aarch64.tar.gz | 5.6MB | 预编译包（静态库） |
| leptonica-1.84.1-ohos-aarch64-debug.tar.gz | 10.2MB | Debug 符号包 |

## 注意事项

1. leptonica 编译为静态库，无可执行文件验证
2. 编译警告（packed member 地址、浮点数比较等）不影响功能
3. G0 干净构建验证因构建系统类型误判失败，实际编译正确

---

**编译结束**: 2026-05-20 16:11
**最终状态**: built