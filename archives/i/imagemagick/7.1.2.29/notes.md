# imagemagick 7.1.2.29 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码 (GitHub 7.1.2-29 tag)
2. 修补 config.guess/config.sub (E007)
3. 修补 configure umask 077→022 (E011)
4. `./configure --prefix=$DEFAULT_PREFIX --disable-openmp --without-heic ...`
5. `make -j2`
6. `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | E007 | patch-autotools-ohos.pl |
| 2 | config.status Permission denied | E011 umask 077 | 补丁 0003 改 umask 022 |
| 3 | GitHub 下载超时 | E017 | ghfast.top 代理 |
| 4 | zlib 版本冲突 1.3.1 vs 1.3.1.1 | 下游 libpng 要求 1.3.1.1 | 更新依赖版本 |
| 5 | test_package 头文件找不到 | include 路径非标准 | cpp_info.includedirs |
| 6 | MAGICKCORE_QUANTUM_DEPTH 未定义 | 编译宏缺失 | cpp_info.defines |

## 补丁

| 文件 | 修改 | 知识库 |
|------|------|--------|
| 0001-config-config.guess.patch | 添加 HarmonyOS 检测 | E007 |
| 0002-config-config.sub.patch | 添加 ohos-linux 三元组 | E007 |
| 0003-configure-umask.patch | umask 077→022 | E011 |

## 依赖版本

- zlib/1.3.1.1
- libjpeg-turbo/3.2.0
- libpng/1.6.58
- libtiff/4.7.2

## 验证结果

```
conan create: PASS (G0-G4 + L2/L4/L5)
test_imagemagick: PASS - MagickWand created 100x100 image
W3 CI 模拟: PASS
```

---

**编译结束**: 2026-08-06 21:35
**最终状态**: built
