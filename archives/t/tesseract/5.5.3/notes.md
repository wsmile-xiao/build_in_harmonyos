# tesseract 5.5.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: tesseract-5.5.3.tar.gz (GitHub 官方 release)
2. 解压并进入源码目录
3. 应用 NEON SIMD 检测补丁 (0001-src-arch-simddetect.cpp.patch)
4. conan install --requires=leptonica/1.87.0 --build=missing (生成 CMakeDeps + CMakeToolchain)
5. cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TRAINING_TOOLS=OFF -DGRAPHICS_DISABLED=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake
6. make -j2
7. make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | NEON 链接错误 | aarch64 平台 HAVE_NEON 未定义但 neon_available_=true | 修改 simddetect.cpp 用 HAVE_NEON 守卫 |
| 2 | 训练工具编译失败 | 依赖 pango/cairo 不可用 | BUILD_TRAINING_TOOLS=OFF |
| 3 | ScrollView 链接错误 | 图形界面依赖不可用 | GRAPHICS_DISABLED=ON |

## 源码修改

补丁: 0001-src-arch-simddetect.cpp.patch
- 修改文件: src/arch/simddetect.cpp
- 修改内容: 将 #if defined(__aarch64__) 改为 #if defined(HAVE_NEON) && defined(__aarch64__)，添加 #elif defined(__aarch64__) 分支设 neon_available_=false

## 依赖版本

- leptonica/1.87.0 (已发布到制品仓)
- zlib/1.3.1 (已发布到制品仓)

## 验证结果

```bash
$ tesseract --version
tesseract 5.5.3
 leptonica-1.87.0
  zlib 1.3.1
 Found libcurl/8.15.0

$ ./test_tesseract
tesseract version: 5.5.3
test tesseract 5.5.3: OK

# CI 结果: L0=pass L1=pass L2=pass L4=pass L5=pass L1e=pass (100%)
```

## 注意事项

- tesseract 既有库 (libtesseract.a) 又有可执行文件 (tesseract binary)，需 commands.json (R38)
- 5.5.3 代码与 5.3.3 的 SIMD 检测逻辑相同，补丁策略一致
- 5.5.0 移除了 TensorFlow 支持，减少了依赖

---

**编译结束**: 2026-08-11 10:20
**最终状态**: published
